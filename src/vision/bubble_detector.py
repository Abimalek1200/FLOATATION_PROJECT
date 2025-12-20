"""
Bubble Detection using Watershed Segmentation

Implements tested algorithm for detecting and measuring individual bubbles
in froth flotation using distance transform + watershed + contour analysis.

Key features:
- Distance transform for finding bubble centers
- Watershed segmentation for separating touching bubbles
- Contour detection with circularity filtering
- Diameter calculation and visualization
"""

import cv2 as cv
import numpy as np
import logging
from typing import List, Tuple, Dict, Any

logger = logging.getLogger(__name__)


class BubbleDetector:
    """Detects individual bubbles using watershed segmentation and contour analysis.
    
    Uses tested parameters optimized for froth flotation bubble detection.
    """
    
    def __init__(
        self,
        min_area: int = 80,
        distance_threshold: float = 0.125,
        circularity_threshold: float = 0.45,
        watershed_dilation_iterations: int = 3
    ):
        """Initialize bubble detector with tested parameters.
        
        Args:
            min_area: Minimum bubble area in pixels² (default: 80)
            distance_threshold: Distance transform threshold multiplier (default: 0.125)
            circularity_threshold: Minimum circularity (0-1, default: 0.45)
            watershed_dilation_iterations: Dilation iterations for watershed (default: 3)
        """
        self.min_area = min_area
        self.distance_threshold = distance_threshold
        self.circularity_threshold = circularity_threshold
        self.watershed_dilation_iterations = watershed_dilation_iterations
        
        # Create kernel for watershed operations
        self.kernel = cv.getStructuringElement(cv.MORPH_ELLIPSE, (1, 1))
        
        logger.info(
            f"BubbleDetector initialized: min_area={min_area}, "
            f"dist_thresh={distance_threshold}, circ_thresh={circularity_threshold}"
        )
    
    def detect(
        self, 
        binary_mask: np.ndarray, 
        original_img: np.ndarray
    ) -> Dict[str, Any]:
        """Detect bubbles in preprocessed binary mask.
        
        Args:
            binary_mask: Binary mask from preprocessor (closing result)
            original_img: Original BGR image for watershed and visualization
        
        Returns:
            Dictionary containing:
                - 'count': Number of detected bubbles
                - 'diameters': List of bubble diameters in pixels
                - 'avg_diameter': Average bubble diameter
                - 'areas': List of bubble areas in pixels²
                - 'centers': List of bubble center coordinates (x, y)
                - 'radii': List of bubble radii
                - 'markers': Watershed markers image
                - 'mask': Final bubble mask (excluding watershed borders)
                - 'contours': Detected contours
        """
        if binary_mask is None or binary_mask.size == 0:
            logger.error("Invalid binary mask")
            return self._empty_result()
        
        try:
            # Step 1: Distance transform
            # Calculates distance from each white pixel to nearest black pixel
            dist = cv.distanceTransform(binary_mask, cv.DIST_L2, 5)
            
            # Step 2: Threshold distance transform to find sure foreground (bubble centers)
            # Use adaptive threshold based on maximum distance
            threshold_value = self.distance_threshold * dist.max()
            _, sure_fg = cv.threshold(dist, threshold_value, 255, 0)
            sure_fg = np.uint8(sure_fg)
            
            # Step 3: Dilate binary mask to find sure background
            sure_bg = cv.dilate(
                binary_mask, 
                self.kernel, 
                iterations=self.watershed_dilation_iterations
            )
            
            # Step 4: Find unknown region (neither sure foreground nor background)
            unknown = cv.subtract(sure_bg, sure_fg)
            
            # Step 5: Label connected components in sure foreground
            ret, markers = cv.connectedComponents(sure_fg)
            
            # Step 6: Add 1 to all markers (so background is not 0, but 1)
            markers = markers + 1
            
            # Step 7: Mark unknown region with 0
            markers[unknown == 255] = 0
            
            # Step 8: Apply watershed algorithm
            # Watershed needs 3-channel image
            markers_ws = markers.copy()
            cv.watershed(cv.cvtColor(original_img, cv.COLOR_BGR2RGB), markers_ws)
            
            # Step 9: Create mask of detected regions (exclude watershed borders marked as -1)
            mask = np.zeros_like(binary_mask, dtype=np.uint8)
            mask[markers_ws > 1] = 255
            
            # Step 10: Find contours in the mask
            contours, _ = cv.findContours(mask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
            
            # Step 11: Analyze contours and filter bubbles
            bubbles = self._analyze_contours(contours)
            
            return {
                'count': bubbles['count'],
                'diameters': bubbles['diameters'],
                'avg_diameter': bubbles['avg_diameter'],
                'areas': bubbles['areas'],
                'centers': bubbles['centers'],
                'radii': bubbles['radii'],
                'circularities': bubbles['circularities'],
                'markers': markers_ws,
                'mask': mask,
                'contours': bubbles['valid_contours'],
                'distance_transform': dist,
                'sure_foreground': sure_fg,
                'unknown_region': unknown
            }
            
        except Exception as e:
            logger.error(f"Bubble detection error: {e}")
            return self._empty_result()
    
    def _analyze_contours(self, contours: List) -> Dict[str, Any]:
        """Analyze contours to extract bubble metrics.
        
        Args:
            contours: List of contours from cv.findContours
        
        Returns:
            Dictionary with bubble metrics
        """
        diameters = []
        areas = []
        centers = []
        radii = []
        circularities = []
        valid_contours = []
        
        for cnt in contours:
            # Calculate area
            area = cv.contourArea(cnt)
            
            # Filter by minimum area
            if area < self.min_area:
                continue
            
            # Calculate perimeter
            peri = cv.arcLength(cnt, True)
            if peri <= 0:
                continue
            
            # Calculate circularity (4π × Area / Perimeter²)
            # Perfect circle = 1.0, square ≈ 0.785
            circularity = 4 * np.pi * area / (peri * peri)
            
            # Filter non-circular shapes
            if circularity < self.circularity_threshold:
                continue
            
            # Calculate equivalent diameter (diameter of circle with same area)
            diameter = 2.0 * np.sqrt(area / np.pi)
            
            # Find minimum enclosing circle
            (x, y), r = cv.minEnclosingCircle(cnt)
            center = (int(x), int(y))
            radius = int(round(r))
            
            # Store metrics
            diameters.append(diameter)
            areas.append(area)
            centers.append(center)
            radii.append(radius)
            circularities.append(circularity)
            valid_contours.append(cnt)
        
        avg_diameter = float(np.mean(diameters)) if diameters else 0.0
        
        return {
            'count': len(diameters),
            'diameters': diameters,
            'avg_diameter': avg_diameter,
            'areas': areas,
            'centers': centers,
            'radii': radii,
            'circularities': circularities,
            'valid_contours': valid_contours
        }
    
    def visualize(
        self, 
        img: np.ndarray, 
        detection_result: Dict[str, Any],
        show_labels: bool = True,
        circle_color: Tuple[int, int, int] = (0, 255, 0),
        text_color: Tuple[int, int, int] = (0, 255, 0)
    ) -> np.ndarray:
        """Draw detected bubbles on image.
        
        Args:
            img: Original BGR image
            detection_result: Result from detect() method
            show_labels: Whether to show bubble number and diameter labels
            circle_color: Color for bubble circles (B, G, R)
            text_color: Color for text labels (B, G, R)
        
        Returns:
            Annotated image with bubbles marked
        """
        out = img.copy()
        
        centers = detection_result.get('centers', [])
        radii = detection_result.get('radii', [])
        diameters = detection_result.get('diameters', [])
        
        font = cv.FONT_HERSHEY_SIMPLEX
        
        for i, (center, radius, diameter) in enumerate(zip(centers, radii, diameters), 1):
            # Draw circle around bubble
            cv.circle(out, center, radius, circle_color, 2)
            
            # Add label with bubble number and diameter
            if show_labels:
                label = f"{i}:{diameter:.1f}px"
                label_pos = (center[0] - radius, center[1] - radius - 6)
                cv.putText(
                    out, label, label_pos,
                    font, 0.4, text_color, 1, cv.LINE_AA
                )
        
        return out
    
    def get_summary_stats(self, detection_result: Dict[str, Any]) -> Dict[str, float]:
        """Calculate summary statistics from detection result.
        
        Args:
            detection_result: Result from detect() method
        
        Returns:
            Dictionary with summary statistics
        """
        diameters = detection_result.get('diameters', [])
        areas = detection_result.get('areas', [])
        circularities = detection_result.get('circularities', [])
        
        if not diameters:
            return {
                'count': 0,
                'avg_diameter': 0.0,
                'std_diameter': 0.0,
                'min_diameter': 0.0,
                'max_diameter': 0.0,
                'avg_area': 0.0,
                'avg_circularity': 0.0
            }
        
        return {
            'count': len(diameters),
            'avg_diameter': float(np.mean(diameters)),
            'std_diameter': float(np.std(diameters)),
            'min_diameter': float(np.min(diameters)),
            'max_diameter': float(np.max(diameters)),
            'avg_area': float(np.mean(areas)),
            'avg_circularity': float(np.mean(circularities))
        }
    
    def _empty_result(self) -> Dict[str, Any]:
        """Return empty detection result."""
        return {
            'count': 0,
            'diameters': [],
            'avg_diameter': 0.0,
            'areas': [],
            'centers': [],
            'radii': [],
            'circularities': [],
            'markers': None,
            'mask': None,
            'contours': [],
            'distance_transform': None,
            'sure_foreground': None,
            'unknown_region': None
        }


if __name__ == "__main__":
    # Test bubble detector
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("Testing bubble detector...")
    
    # Create test binary mask with circles
    test_mask = np.zeros((480, 640), dtype=np.uint8)
    cv.circle(test_mask, (100, 100), 30, 255, -1)
    cv.circle(test_mask, (300, 200), 45, 255, -1)
    cv.circle(test_mask, (500, 300), 25, 255, -1)
    cv.circle(test_mask, (200, 400), 35, 255, -1)
    
    # Create test color image
    test_img = np.zeros((480, 640, 3), dtype=np.uint8)
    test_img[:] = (50, 50, 50)
    test_img[test_mask == 255] = (200, 200, 200)
    
    # Detect bubbles
    detector = BubbleDetector()
    result = detector.detect(test_mask, test_img)
    
    print(f"\nDetection Results:")
    print(f"Bubble count: {result['count']}")
    print(f"Average diameter: {result['avg_diameter']:.2f} px")
    print(f"Diameters: {[f'{d:.1f}' for d in result['diameters']]}")
    
    # Get summary stats
    stats = detector.get_summary_stats(result)
    print(f"\nSummary Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value:.2f}")
    
    # Visualize
    annotated = detector.visualize(test_img, result)
    print(f"\nAnnotated image shape: {annotated.shape}")
    print("Bubble detection test completed successfully!")
