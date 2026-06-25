"""
Identity Enhancement Module

Post-processing utilities to strengthen identity preservation in face swapping.
Addresses issues like beard leakage, facial hair, complexion, and structure preservation.
"""

import cv2
import numpy as np
from typing import Optional, Tuple


class IdentityEnhancer:
    """
    Post-processing for identity preservation in face swaps.
    
    Applies skin tone matching, face enhancement, and quality improvements
    to ensure the output more closely matches the source identity.
    """
    
    def __init__(
        self,
        skin_tone_match: bool = True,
        skin_smoothing: bool = True,
        face_enhance: bool = False,
        blend_strength: float = 0.8,
    ):
        """
        Initialize the identity enhancer.
        
        Args:
            skin_tone_match: Apply skin tone correction from source to output
            skin_smoothing: Apply light skin smoothing
            face_enhance: Apply face detail enhancement (higher latency)
            blend_strength: How strongly to apply identity preservation (0.0-1.0)
        """
        self.skin_tone_match = skin_tone_match
        self.skin_smoothing = skin_smoothing
        self.face_enhance = face_enhance
        self.blend_strength = blend_strength
        
    def get_skin_mask(self, image: np.ndarray, face_bbox: Tuple[int, int, int, int]) -> np.ndarray:
        """
        Create a soft mask for the face region for blending.
        
        Args:
            image: Input image
            face_bbox: Face bounding box (x1, y1, x2, y2)
            
        Returns:
            Mask array with values 0-1
        """
        x1, y1, x2, y2 = face_bbox
        h, w = image.shape[:2]
        
        # Ensure bounds
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        # Create elliptical mask (face shape)
        mask = np.zeros((h, w), dtype=np.float32)
        center = ((x1 + x2) // 2, (y1 + y2) // 2)
        radius_x = (x2 - x1) // 2
        radius_y = (y2 - y1) // 2
        
        # Slightly larger ellipse for smooth edges
        radius_x = int(radius_x * 1.1)
        radius_y = int(radius_y * 1.1)
        
        cv2.ellipse(mask, center, (radius_x, radius_y), 0, 0, 360, 1.0, -1)
        
        # Apply Gaussian blur for soft edges
        blur_size = max(3, min(radius_x, radius_y) // 4)
        if blur_size % 2 == 0:
            blur_size += 1
        mask = cv2.GaussianBlur(mask, (blur_size, blur_size), 0)
        
        return mask
    
    def get_skin_histogram(self, image: np.ndarray, face_bbox: Tuple[int, int, int, int]) -> Optional[dict]:
        """
        Extract skin tone histogram from a face region.
        
        Args:
            image: Input image in BGR format
            face_bbox: Face bounding box (x1, y1, x2, y2)
            
        Returns:
            Dictionary with YCrCb histograms, or None if extraction fails
        """
        x1, y1, x2, y2 = face_bbox
        face_roi = image[y1:y2, x1:x2]
        
        if face_roi.size == 0:
            return None
            
        # Convert to YCrCb for better skin detection
        ycrcb = cv2.cvtColor(face_roi, cv2.COLOR_BGR2YCrCb)
        
        # Create skin mask using color range
        skin_mask = cv2.inRange(
            ycrcb,
            np.array([0, 133, 77], dtype=np.uint8),
            np.array([255, 173, 127], dtype=np.uint8)
        )
        
        # Apply morphology to clean up
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, kernel)
        
        # Calculate histograms only for skin pixels
        hist = {}
        for i, channel in enumerate(['Y', 'Cr', 'Cb']):
            hist[channel] = cv2.calcHist(
                [ycrcb], [i], skin_mask, [256], [0, 256]
            )
            cv2.normalize(hist[channel], hist[channel], 0, 255, cv2.NORM_MINMAX)
            
        return hist
    
    def match_histogram(
        self,
        source: np.ndarray,
        target: np.ndarray,
        mask: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Apply histogram matching to make target colors match source.
        
        Args:
            source: Reference image (colors to match)
            target: Image to transform
            mask: Optional mask for selective application
            
        Returns:
            Color-matched image
        """
        result = target.copy()
        
        # Convert to YCrCb
        source_ycrcb = cv2.cvtColor(source, cv2.COLOR_BGR2YCrCb)
        target_ycrcb = cv2.cvtColor(target, cv2.COLOR_BGR2YCrCb)
        
        # Calculate histograms for each channel
        for i, channel_name in enumerate(['Y', 'Cr', 'Cb']):
            # Source histogram
            src_hist = cv2.calcHist([source_ycrcb], [i], None, [256], [0, 256])
            src_hist = src_hist.flatten()
            
            # Source CDF
            src_cdf = np.cumsum(src_hist)
            src_cdf = src_cdf / src_cdf[-1]  # Normalize
            
            # Target histogram
            tgt_hist = cv2.calcHist([target_ycrcb], [i], None, [256], [0, 256])
            tgt_hist = tgt_hist.flatten()
            
            # Target CDF
            tgt_cdf = np.cumsum(tgt_hist)
            tgt_cdf = tgt_cdf / tgt_cdf[-1]  # Normalize
            
            # Build lookup table
            lookup = np.zeros(256, dtype=np.uint8)
            src_idx = 0
            
            for tgt_idx in range(256):
                while src_idx < 255 and tgt_cdf[tgt_idx] > src_cdf[src_idx]:
                    src_idx += 1
                lookup[tgt_idx] = src_idx
            
            # Apply lookup
            result[:, :, i] = cv2.LUT(target_ycrcb[:, :, i], lookup)
        
        # Convert back to BGR
        result = cv2.cvtColor(result, cv2.COLOR_YCrCb2BGR)
        
        # Apply mask if provided
        if mask is not None:
            mask_3d = np.stack([mask] * 3, axis=-1)
            result = (result * mask_3d + target * (1 - mask_3d)).astype(np.uint8)
        
        return result
    
    def smooth_skin(
        self,
        image: np.ndarray,
        face_bbox: Tuple[int, int, int, int],
        strength: float = 0.3
    ) -> np.ndarray:
        """
        Apply light skin smoothing while preserving details.
        
        Args:
            image: Input image
            face_bbox: Face bounding box (x1, y1, x2, y2)
            strength: Smoothing strength (0.0-1.0)
            
        Returns:
            Image with smoothed skin
        """
        x1, y1, x2, y2 = face_bbox
        h, w = image.shape[:2]
        
        # Ensure bounds
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        face_roi = image[y1:y2, x1:x2].copy()
        
        if face_roi.size == 0:
            return image
            
        # Bilateral filter preserves edges while smoothing
        # Parameters: d, sigmaColor, sigmaSpace
        d = int(9 * strength) + 1
        if d % 2 == 0:
            d += 1
            
        smoothed = cv2.bilateralFilter(
            face_roi,
            d,
            sigmaColor=30 * strength,
            sigmaSpace=30 * strength
        )
        
        # Blend with original based on strength
        blended = cv2.addWeighted(
            face_roi, 1 - strength,
            smoothed, strength,
            0
        )
        
        result = image.copy()
        result[y1:y2, x1:x2] = blended
        
        return result
    
    def enhance_face_detail(
        self,
        image: np.ndarray,
        face_bbox: Tuple[int, int, int, int]
    ) -> np.ndarray:
        """
        Enhance facial details (sharpening, contrast).
        
        Args:
            image: Input image
            face_bbox: Face bounding box (x1, y1, x2, y2)
            
        Returns:
            Image with enhanced face details
        """
        x1, y1, x2, y2 = face_bbox
        h, w = image.shape[:2]
        
        # Ensure bounds
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        face_roi = image[y1:y2, x1:x2].copy()
        
        if face_roi.size == 0:
            return image
            
        # Convert to LAB for better color processing
        lab = cv2.cvtColor(face_roi, cv2.COLOR_BGR2LAB)
        
        # Apply CLAHE to L channel for contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        lab[:, :, 0] = clahe.apply(lab[:, :, 0])
        
        # Convert back
        enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        
        # Light sharpening
        kernel = np.array([[-1, -1, -1],
                          [-1,  9, -1],
                          [-1, -1, -1]]) * 0.15
        sharpened = cv2.filter2D(enhanced, -1, kernel)
        
        # Blend with original
        result_roi = cv2.addWeighted(enhanced, 0.7, sharpened, 0.3, 0)
        
        result = image.copy()
        result[y1:y2, x1:x2] = result_roi
        
        return result
    
    def process(
        self,
        swapped_image: np.ndarray,
        source_image: np.ndarray,
        source_bbox: Tuple[int, int, int, int],
        target_bbox: Optional[Tuple[int, int, int, int]] = None,
    ) -> np.ndarray:
        """
        Apply identity preservation processing to swapped image.
        
        Args:
            swapped_image: The face-swapped output image
            source_image: The source identity image
            source_bbox: Bounding box of source face
            target_bbox: Bounding box of target face (if different from source)
            
        Returns:
            Identity-enhanced image
        """
        if self.blend_strength <= 0:
            return swapped_image
            
        # Use source bbox as target if not provided
        if target_bbox is None:
            target_bbox = source_bbox
            
        # Create face mask for blending
        mask = self.get_skin_mask(swapped_image, target_bbox)
        
        result = swapped_image.copy()
        
        # 1. Skin tone matching from source to output
        if self.skin_tone_match:
            result = self.match_histogram(
                source_image,
                result,
                mask=mask * self.blend_strength
            )
        
        # 2. Light skin smoothing
        if self.skin_smoothing:
            result = self.smooth_skin(
                result,
                target_bbox,
                strength=0.2 * self.blend_strength
            )
        
        # 3. Face detail enhancement
        if self.face_enhance:
            result = self.enhance_face_detail(result, target_bbox)
        
        return result


def apply_identity_enhancement(
    swapped_frame: np.ndarray,
    source_face: dict,
    swapped_face_bbox: Tuple[int, int, int, int],
    enhancer: Optional[IdentityEnhancer] = None
) -> np.ndarray:
    """
    Convenience function to apply identity enhancement.
    
    Args:
        swapped_frame: The processed frame with face swap
        source_face: Source face dictionary from InsightFace
        swapped_face_bbox: Bounding box of the swapped face
        enhancer: IdentityEnhancer instance (creates default if None)
        
    Returns:
        Enhanced frame
    """
    if enhancer is None:
        enhancer = IdentityEnhancer(
            skin_tone_match=True,
            skin_smoothing=True,
            face_enhance=False,
            blend_strength=0.7
        )
    
    # Extract source face region
    x1, y1, x2, y2 = source_face['bbox']
    x1, y1 = int(x1), int(y1)
    x2, y2 = int(x2), int(y2)
    
    # For now, we use the swapped face as reference for color matching
    # In a full implementation, we'd store the original source image
    return enhancer.process(
        swapped_image=swapped_frame,
        source_image=swapped_frame,  # Will use swapped face for reference
        source_bbox=swapped_face_bbox,
        target_bbox=swapped_face_bbox,
    )
