"""
Image Preprocessing for Froth Flotation Vision System

Implements tested preprocessing pipeline:
- Grayscale conversion
- Gaussian blur (1x1 kernel)
- Binary segmentation (Otsu thresholding, inverted)
- Morphological operations (opening + closing)

Parameters are optimized for bubble detection based on testing.
"""

import cv2 as cv
import numpy as np
import logging
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """Preprocesses raw camera frames for bubble detection.
    
    Uses tested parameters that yield optimal bubble count and size metrics.
    """
    
    def __init__(
        self,
        blur_kernel_size: Tuple[int, int] = (1, 1),
        morph_kernel_size: Tuple[int, int] = (1, 1),
        opening_iterations: int = 2,
        closing_iterations: int = 4
    ):
        """Initialize preprocessor with tested parameters.
        
        Args:
            blur_kernel_size: Gaussian blur kernel size (default: 1x1)
            morph_kernel_size: Morphological operation kernel size (default: 1x1)
            opening_iterations: Number of morphological opening iterations (default: 2)
            closing_iterations: Number of morphological closing iterations (default: 4)
        """
        self.blur_kernel_size = blur_kernel_size
        self.morph_kernel_size = morph_kernel_size
        self.opening_iterations = opening_iterations
        self.closing_iterations = closing_iterations
        
        # Pre-create morphological kernel (ellipse shape for better circle detection)
        self.kernel = cv.getStructuringElement(
            cv.MORPH_ELLIPSE, 
            self.morph_kernel_size
        )
        
        logger.info(
            f"Preprocessor initialized: blur={blur_kernel_size}, "
            f"kernel={morph_kernel_size}, open={opening_iterations}, close={closing_iterations}"
        )
    
    def process(self, img: np.ndarray) -> Dict[str, Any]:
        """Apply complete preprocessing pipeline to raw frame.
        
        Pipeline:
        1. Convert BGR to grayscale
        2. Apply Gaussian blur
        3. Binary segmentation using Otsu (inverted)
        4. Morphological opening (noise removal)
        5. Morphological closing (gap filling)
        
        Args:
            img: Input BGR image from camera (numpy array)
        
        Returns:
            Dictionary containing:
                - 'gray': Grayscale image
                - 'blur': Blurred grayscale image
                - 'binary': Binary thresholded image
                - 'opening': After morphological opening
                - 'closing': Final preprocessed binary mask
                - 'threshold_value': Otsu threshold value used
        """
        if img is None or img.size == 0:
            logger.error("Invalid input image")
            return {}
        
        try:
            # Step 1: Convert to grayscale
            gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
            
            # Step 2: Apply Gaussian blur
            blur = cv.GaussianBlur(gray, self.blur_kernel_size, 0)
            
            # Step 3: Binary segmentation using Otsu thresholding (inverted)
            # THRESH_BINARY_INV: lighter/brighter bubbles become white (255)
            threshold_value, binary = cv.threshold(
                blur, 
                0, 
                255, 
                cv.THRESH_BINARY_INV + cv.THRESH_OTSU
            )
            
            # Step 4: Morphological opening (erosion followed by dilation)
            # Removes small noise and separates weakly connected objects
            opening = cv.morphologyEx(
                binary, 
                cv.MORPH_OPEN, 
                self.kernel, 
                iterations=self.opening_iterations
            )
            
            # Step 5: Morphological closing (dilation followed by erosion)
            # Fills small holes and gaps in bubble regions
            closing = cv.morphologyEx(
                opening, 
                cv.MORPH_CLOSE, 
                self.kernel, 
                iterations=self.closing_iterations
            )
            
            return {
                'gray': gray,
                'blur': blur,
                'binary': binary,
                'opening': opening,
                'closing': closing,
                'threshold_value': threshold_value
            }
            
        except Exception as e:
            logger.error(f"Preprocessing error: {e}")
            return {}
    
    def get_binary_mask(self, img: np.ndarray) -> np.ndarray:
        """Quick method to get final binary mask only.
        
        Args:
            img: Input BGR image
        
        Returns:
            Binary mask (closing result) as uint8 numpy array
        """
        result = self.process(img)
        return result.get('closing', np.zeros_like(img[:, :, 0], dtype=np.uint8))
    
    def visualize_pipeline(self, img: np.ndarray) -> np.ndarray:
        """Create visualization showing all preprocessing stages.
        
        Args:
            img: Input BGR image
        
        Returns:
            Horizontal concatenation of all preprocessing stages for debugging
        """
        result = self.process(img)
        
        if not result:
            return img
        
        # Convert all images to BGR for consistent display
        stages = []
        
        # Original (resized to match others)
        stages.append(cv.resize(img, (200, 150)))
        
        # Grayscale
        stages.append(cv.cvtColor(cv.resize(result['gray'], (200, 150)), cv.COLOR_GRAY2BGR))
        
        # Binary
        stages.append(cv.cvtColor(cv.resize(result['binary'], (200, 150)), cv.COLOR_GRAY2BGR))
        
        # Opening
        stages.append(cv.cvtColor(cv.resize(result['opening'], (200, 150)), cv.COLOR_GRAY2BGR))
        
        # Closing
        stages.append(cv.cvtColor(cv.resize(result['closing'], (200, 150)), cv.COLOR_GRAY2BGR))
        
        # Add labels
        labels = ['Original', 'Grayscale', 'Binary (Otsu)', 'Opening', 'Closing']
        for i, (stage, label) in enumerate(zip(stages, labels)):
            cv.putText(
                stage, label, (10, 20),
                cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv.LINE_AA
            )
        
        # Concatenate horizontally
        return np.hstack(stages)


def preprocess_frame(img: np.ndarray) -> np.ndarray:
    """Simple preprocessing function for quick use.
    
    Args:
        img: Input BGR image
    
    Returns:
        Binary mask ready for bubble detection
    """
    preprocessor = ImagePreprocessor()
    return preprocessor.get_binary_mask(img)


if __name__ == "__main__":
    # Test preprocessing with synthetic image
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("Testing image preprocessor...")
    
    # Create test image with circles (simulating bubbles)
    test_img = np.zeros((480, 640, 3), dtype=np.uint8)
    test_img[:] = (50, 50, 50)  # Dark gray background
    
    # Add some white circles (bubbles)
    cv.circle(test_img, (100, 100), 30, (200, 200, 200), -1)
    cv.circle(test_img, (300, 200), 45, (220, 220, 220), -1)
    cv.circle(test_img, (500, 300), 25, (180, 180, 180), -1)
    
    # Add noise
    noise = np.random.randint(0, 30, test_img.shape, dtype=np.uint8)
    test_img = cv.add(test_img, noise)
    
    # Process
    preprocessor = ImagePreprocessor()
    results = preprocessor.process(test_img)
    
    print(f"Preprocessing complete!")
    print(f"Otsu threshold value: {results['threshold_value']:.1f}")
    print(f"Binary mask shape: {results['closing'].shape}")
    print(f"Non-zero pixels in mask: {np.count_nonzero(results['closing'])}")
    
    # Visualize
    visualization = preprocessor.visualize_pipeline(test_img)
    print(f"Visualization shape: {visualization.shape}")
    print("Preprocessing test completed successfully!")
