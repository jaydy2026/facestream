import asyncio
from pathlib import Path
from typing import Optional

import insightface
import numpy as np
import torch
from huggingface_hub import hf_hub_download
from insightface.app.common import Face
from insightface.model_zoo.inswapper import INSwapper

from facestream.constants import MODEL_CACHE_DIR
from facestream.enhance import IdentityEnhancer, apply_identity_enhancement


class FaceSwap:
    """
    Face swapping service with configurable identity preservation.
    
    Attributes:
        identity_strength: How strongly to preserve source identity (0.0-1.0)
        skin_tone_match: Apply skin tone correction
        skin_smoothing: Apply light skin smoothing
    """
    
    def _download_faceswap_model(self):
        hf_hub_download(
            "hacksider/deep-live-cam",
            "inswapper_128_fp16.onnx",
            local_dir=MODEL_CACHE_DIR,
        )

    def __init__(
        self,
        identity_strength: float = 0.7,
        skin_tone_match: bool = True,
        skin_smoothing: bool = True,
        face_enhance: bool = False,
        paste_back: bool = True,
    ):
        """
        Initialize FaceSwap with identity preservation settings.
        
        Args:
            identity_strength: Strength of identity preservation (0.0-1.0)
                Higher values mean stronger adherence to source identity.
            skin_tone_match: Apply histogram matching for skin tone
            skin_smoothing: Apply bilateral filtering for skin smoothness
            face_enhance: Apply face detail enhancement (adds latency)
            paste_back: Use paste_back for compositing (True recommended)
        """
        self._download_faceswap_model()
        
        # Identity preservation settings
        self.identity_strength = identity_strength
        self.skin_tone_match = skin_tone_match
        self.skin_smoothing = skin_smoothing
        self.face_enhance = face_enhance
        self.paste_back = paste_back

        self.faceswap_model: INSwapper = insightface.model_zoo.get_model(  # pyright: ignore[reportAttributeAccessIssue]
            str(Path(MODEL_CACHE_DIR) / "inswapper_128_fp16.onnx"),
            providers=[
                (
                    "CUDAExecutionProvider",
                    {"device_id": torch.cuda.current_device()},
                )
            ],
        )

        self.faceanalysis = insightface.app.FaceAnalysis(
            name="buffalo_l",
            root=MODEL_CACHE_DIR,
            providers=[
                (
                    "CUDAExecutionProvider",
                    {"device_id": torch.cuda.current_device()},
                )
            ],
        )

        self.faceanalysis.prepare(ctx_id=0, det_size=(640, 640))
        
        # Initialize enhancer
        self.enhancer = IdentityEnhancer(
            skin_tone_match=skin_tone_match,
            skin_smoothing=skin_smoothing,
            face_enhance=face_enhance,
            blend_strength=identity_strength,
        )

    def _swap_face(self, target: np.ndarray, source_face: dict):
        """Perform face swap with optional identity enhancement."""
        source_face_obj = Face(source_face)
        target_face = self._get_one_face(target)

        if target_face is None:
            return target

        # Store target face bbox for potential post-processing
        target_face_bbox = tuple(int(x) for x in target_face.bbox)
        
        # Perform face swap
        result = self.faceswap_model.get(
            target, target_face, source_face_obj, paste_back=self.paste_back
        )
        
        # Apply identity preservation enhancement
        if self.identity_strength > 0:
            result = apply_identity_enhancement(
                swapped_frame=result,
                source_face=source_face,
                swapped_face_bbox=target_face_bbox,
                enhancer=self.enhancer,
            )
        
        return result

    def _get_one_face(self, frame: np.ndarray) -> Optional[dict]:
        """Detect and return the leftmost face in the frame."""
        try:
            faces = self.faceanalysis.get(frame)
            if not faces:
                return None
            return min(faces, key=lambda x: x.bbox[0])
        except ValueError:
            return None

    async def get_one_face(self, frame: np.ndarray) -> Optional[dict]:
        """Async wrapper for face detection."""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._get_one_face, frame)
        return result

    async def swap_face(self, frame: np.ndarray, source_face: dict):
        """Async wrapper for face swapping with identity preservation."""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._swap_face, frame, source_face)
        return result
