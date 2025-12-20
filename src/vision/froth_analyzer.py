"""
Froth Analysis Module

Aggregates bubble detection results into high-level froth metrics for control system.
Calculates froth stability, coverage ratio, and temporal statistics.
"""

import cv2 as cv
import numpy as np
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import deque

from .preprocessor import ImagePreprocessor
from .bubble_detector import BubbleDetector

logger = logging.getLogger(__name__)


class FrothAnalyzer:
    """High-level froth analysis combining preprocessing and bubble detection.
    
    Provides aggregated metrics for control system and anomaly detection.
    """
    
    def __init__(
        self,
        preprocessor: Optional[ImagePreprocessor] = None,
        detector: Optional[BubbleDetector] = None,
        history_size: int = 10
    ):
        """Initialize froth analyzer.
        
        Args:
            preprocessor: ImagePreprocessor instance (creates default if None)
            detector: BubbleDetector instance (creates default if None)
            history_size: Number of historical measurements to keep for temporal analysis
        """
        self.preprocessor = preprocessor or ImagePreprocessor()
        self.detector = detector or BubbleDetector()
        self.history_size = history_size
        
        # Maintain rolling history for temporal statistics
        self.bubble_count_history = deque(maxlen=history_size)
        self.avg_diameter_history = deque(maxlen=history_size)
        self.stability_history = deque(maxlen=history_size)
        
        logger.info(f"FrothAnalyzer initialized with history_size={history_size}")
    
    def analyze(self, img: np.ndarray) -> Dict[str, Any]:
        """Complete froth analysis pipeline.
        
        Args:
            img: Raw BGR image from camera
        
        Returns:
            Dictionary containing all froth metrics:
                - 'bubble_count': Number of detected bubbles
                - 'avg_bubble_size': Average bubble diameter in pixels²
                - 'size_std_dev': Standard deviation of bubble sizes
                - 'froth_stability': Stability score (0-1)
                - 'coverage_ratio': Fraction of image covered by bubbles (0-1)
                - 'timestamp': ISO timestamp of analysis
                - 'min_diameter': Minimum bubble diameter
                - 'max_diameter': Maximum bubble diameter
                - 'avg_circularity': Average bubble circularity
                - 'temporal_variance': Variance over recent history
                - 'annotated_image': Image with bubbles marked (BGR)
                - 'detection_result': Raw detection result from BubbleDetector
                - 'preprocessing_result': Raw preprocessing result
        """
        if img is None or img.size == 0:
            logger.error("Invalid input image")
            return self._empty_metrics()
        
        try:
            # Step 1: Preprocess image
            preprocess_result = self.preprocessor.process(img)
            if not preprocess_result:
                logger.error("Preprocessing failed")
                return self._empty_metrics()
            
            binary_mask = preprocess_result['closing']
            
            # Step 2: Detect bubbles
            detection_result = self.detector.detect(binary_mask, img)
            
            # Step 3: Calculate coverage ratio
            coverage_ratio = self._calculate_coverage_ratio(binary_mask, img.shape[:2])
            
            # Step 4: Calculate froth stability
            bubble_count = detection_result['count']
            avg_diameter = detection_result['avg_diameter']
            diameters = detection_result['diameters']
            
            # Update history
            self.bubble_count_history.append(bubble_count)
            self.avg_diameter_history.append(avg_diameter)
            
            # Calculate stability (based on size variance and temporal consistency)
            size_std_dev = float(np.std(diameters)) if diameters else 0.0
            froth_stability = self._calculate_stability(
                avg_diameter, 
                size_std_dev,
                bubble_count
            )
            self.stability_history.append(froth_stability)
            
            # Step 5: Calculate temporal variance (rate of change)
            temporal_variance = self._calculate_temporal_variance()
            
            # Step 6: Get summary statistics
            stats = self.detector.get_summary_stats(detection_result)
            
            # Step 7: Create annotated visualization
            annotated_image = self.detector.visualize(img, detection_result)
            
            # Add summary text overlay
            annotated_image = self._add_summary_overlay(
                annotated_image,
                bubble_count,
                avg_diameter,
                froth_stability,
                coverage_ratio
            )
            
            # Step 8: Compile metrics
            timestamp = datetime.now()
            
            metrics = {
                # Core metrics (used by control system)
                'bubble_count': bubble_count,
                'avg_bubble_size': float(np.mean([d**2 for d in diameters])) if diameters else 0.0,  # pixels²
                'size_std_dev': size_std_dev,
                'froth_stability': froth_stability,
                'coverage_ratio': coverage_ratio,
                'timestamp': timestamp.isoformat(),
                
                # Extended metrics
                'avg_diameter': avg_diameter,
                'min_diameter': stats['min_diameter'],
                'max_diameter': stats['max_diameter'],
                'avg_circularity': stats['avg_circularity'],
                'temporal_variance': temporal_variance,
                
                # Visualization and debugging
                'annotated_image': annotated_image,
                'detection_result': detection_result,
                'preprocessing_result': preprocess_result
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Froth analysis error: {e}")
            return self._empty_metrics()
    
    def _calculate_coverage_ratio(
        self, 
        binary_mask: np.ndarray, 
        image_shape: tuple
    ) -> float:
        """Calculate fraction of image covered by bubbles.
        
        Args:
            binary_mask: Binary mask of bubbles (white = bubble)
            image_shape: (height, width) of original image
        
        Returns:
            Coverage ratio (0-1)
        """
        total_pixels = image_shape[0] * image_shape[1]
        bubble_pixels = np.count_nonzero(binary_mask)
        return float(bubble_pixels) / total_pixels if total_pixels > 0 else 0.0
    
    def _calculate_stability(
        self,
        avg_diameter: float,
        size_std_dev: float,
        bubble_count: int
    ) -> float:
        """Calculate froth stability score.
        
        Stability is based on:
        - Low variance in bubble sizes (uniform distribution)
        - Consistent bubble count over time
        - Moderate bubble density (not too few, not too many)
        
        Args:
            avg_diameter: Average bubble diameter
            size_std_dev: Standard deviation of bubble sizes
            bubble_count: Number of bubbles detected
        
        Returns:
            Stability score (0-1, higher = more stable)
        """
        # Component 1: Size uniformity (low std dev = high stability)
        if avg_diameter > 0:
            coefficient_of_variation = size_std_dev / avg_diameter
            size_uniformity = 1.0 / (1.0 + coefficient_of_variation)
        else:
            size_uniformity = 0.0
        
        # Component 2: Temporal consistency (low variance in count over time)
        if len(self.bubble_count_history) >= 3:
            count_std = float(np.std(list(self.bubble_count_history)))
            count_mean = float(np.mean(list(self.bubble_count_history)))
            if count_mean > 0:
                count_consistency = 1.0 / (1.0 + count_std / count_mean)
            else:
                count_consistency = 0.0
        else:
            count_consistency = 0.5  # Neutral when insufficient history
        
        # Component 3: Bubble density score (prefer moderate counts)
        # Optimal range: 50-200 bubbles
        if bubble_count < 50:
            density_score = bubble_count / 50.0
        elif bubble_count > 200:
            density_score = 1.0 - min((bubble_count - 200) / 200.0, 0.5)
        else:
            density_score = 1.0
        
        # Weighted combination
        stability = (
            0.4 * size_uniformity +
            0.4 * count_consistency +
            0.2 * density_score
        )
        
        return np.clip(stability, 0.0, 1.0)
    
    def _calculate_temporal_variance(self) -> float:
        """Calculate rate of change in bubble count.
        
        Returns:
            Temporal variance (0 = stable, higher = more change)
        """
        if len(self.bubble_count_history) < 2:
            return 0.0
        
        # Calculate variance in bubble count over history
        variance = float(np.var(list(self.bubble_count_history)))
        return variance
    
    def _add_summary_overlay(
        self,
        img: np.ndarray,
        bubble_count: int,
        avg_diameter: float,
        stability: float,
        coverage: float
    ) -> np.ndarray:
        """Add summary text overlay to annotated image.
        
        Args:
            img: Annotated image
            bubble_count: Bubble count
            avg_diameter: Average diameter
            stability: Stability score
            coverage: Coverage ratio
        
        Returns:
            Image with text overlay
        """
        font = cv.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 2
        color = (0, 255, 255)  # Yellow
        
        # Add semi-transparent background for text
        overlay = img.copy()
        cv.rectangle(overlay, (10, 10), (350, 120), (0, 0, 0), -1)
        img = cv.addWeighted(overlay, 0.6, img, 0.4, 0)
        
        # Add text
        y_offset = 35
        cv.putText(img, f"Count: {bubble_count}", (20, y_offset),
                   font, font_scale, color, thickness, cv.LINE_AA)
        
        y_offset += 30
        cv.putText(img, f"Avg Diam: {avg_diameter:.1f}px", (20, y_offset),
                   font, font_scale, color, thickness, cv.LINE_AA)
        
        y_offset += 30
        cv.putText(img, f"Stability: {stability:.2f}", (20, y_offset),
                   font, font_scale, color, thickness, cv.LINE_AA)
        
        return img
    
    def get_metrics_for_control(self) -> Dict[str, float]:
        """Get simplified metrics for control system.
        
        Returns:
            Dictionary with only the metrics needed by PI controller
        """
        if not self.bubble_count_history:
            return {
                'bubble_count': 0,
                'avg_bubble_size': 0.0,
                'size_std_dev': 0.0,
                'froth_stability': 0.0,
                'coverage_ratio': 0.0
            }
        
        # Return most recent values
        return {
            'bubble_count': int(self.bubble_count_history[-1]),
            'avg_bubble_size': float(self.avg_diameter_history[-1]**2),
            'froth_stability': float(self.stability_history[-1])
        }
    
    def reset_history(self):
        """Clear historical data (useful when restarting control)."""
        self.bubble_count_history.clear()
        self.avg_diameter_history.clear()
        self.stability_history.clear()
        logger.info("Froth analyzer history reset")
    
    def _empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics when analysis fails."""
        return {
            'bubble_count': 0,
            'avg_bubble_size': 0.0,
            'size_std_dev': 0.0,
            'froth_stability': 0.0,
            'coverage_ratio': 0.0,
            'timestamp': datetime.now().isoformat(),
            'avg_diameter': 0.0,
            'min_diameter': 0.0,
            'max_diameter': 0.0,
            'avg_circularity': 0.0,
            'temporal_variance': 0.0,
            'annotated_image': None,
            'detection_result': {},
            'preprocessing_result': {}
        }


if __name__ == "__main__":
    # Test froth analyzer
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("Testing froth analyzer...")
    
    # Create test image with multiple bubbles
    test_img = np.zeros((480, 640, 3), dtype=np.uint8)
    test_img[:] = (50, 50, 50)  # Dark gray background
    
    # Add bubbles with varying sizes
    bubbles = [
        ((100, 100), 30),
        ((250, 150), 40),
        ((400, 120), 35),
        ((150, 300), 45),
        ((350, 280), 25),
        ((500, 350), 38),
    ]
    
    for (x, y), radius in bubbles:
        cv.circle(test_img, (x, y), radius, (200, 200, 200), -1)
    
    # Add noise
    noise = np.random.randint(0, 30, test_img.shape, dtype=np.uint8)
    test_img = cv.add(test_img, noise)
    
    # Analyze froth
    analyzer = FrothAnalyzer(history_size=5)
    
    # Analyze multiple frames to build history
    for i in range(5):
        print(f"\n--- Frame {i+1} ---")
        metrics = analyzer.analyze(test_img)
        
        print(f"Bubble count: {metrics['bubble_count']}")
        print(f"Avg diameter: {metrics['avg_diameter']:.2f}px")
        print(f"Stability: {metrics['froth_stability']:.3f}")
        print(f"Coverage ratio: {metrics['coverage_ratio']:.3f}")
        print(f"Temporal variance: {metrics['temporal_variance']:.2f}")
        
        # Vary bubble count slightly for temporal analysis
        if i < 4:
            test_img = cv.circle(
                test_img, 
                (np.random.randint(50, 590), np.random.randint(50, 430)), 
                np.random.randint(20, 50), 
                (200, 200, 200), 
                -1
            )
    
    print("\n--- Control Metrics ---")
    control_metrics = analyzer.get_metrics_for_control()
    for key, value in control_metrics.items():
        print(f"{key}: {value}")
    
    print("\nFroth analyzer test completed successfully!")
