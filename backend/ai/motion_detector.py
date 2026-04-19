"""
TASK-003: OpenCV Motion Detection Module
=========================================
Detects motion in surveillance frames using background subtraction and
contour analysis.  Produces a normalised MotionResult that downstream
modules (Gemini vision, fusion controller) consume.

Algorithm
---------
1. Convert frame to grayscale and apply Gaussian blur.
2. Maintain a running background model via an exponential average.
3. Compute absolute frame delta from background.
4. Apply binary threshold → dilate → find contours.
5. Filter contours by minimum area and accumulate a motion score.
6. Decide whether this frame should trigger an AI analysis call
   based on a configurable frame-interval counter.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Tuple

import cv2
import numpy as np

from config import get_settings
from models.schemas import MotionResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data class for internal frame state
# ---------------------------------------------------------------------------


@dataclass
class _FrameState:
    """Mutable state carried across successive frames for a single stream."""

    background: Optional[np.ndarray] = None
    frame_counter: int = 0
    consecutive_motion_frames: int = 0


# ---------------------------------------------------------------------------
# MotionDetector
# ---------------------------------------------------------------------------


class MotionDetector:
    """
    Stateful per-camera motion detector based on OpenCV background subtraction.

    Usage
    -----
    >>> detector = MotionDetector()
    >>> result = detector.process_frame(frame_bgr, camera_id="cam-01")
    >>> if result.should_analyze:
    ...     # send frame to Gemini
    """

    def __init__(self) -> None:
        self._cfg = get_settings()
        # One state object per camera_id so multiple streams work independently
        self._states: dict[str, _FrameState] = {}
        logger.info(
            "MotionDetector initialised | "
            "min_contour_area=%d, blur_kernel=%d, threshold=%d",
            self._cfg.motion_min_contour_area,
            self._cfg.motion_gaussian_blur_kernel,
            self._cfg.motion_binary_threshold,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_frame(
        self,
        frame: np.ndarray,
        camera_id: str = "default",
    ) -> MotionResult:
        """
        Process a single BGR frame and return a MotionResult.

        Parameters
        ----------
        frame:      BGR uint8 NumPy array (height × width × 3).
        camera_id:  Identifier used to isolate background state per stream.

        Returns
        -------
        MotionResult with motion metrics and scheduling flag.
        """
        if frame is None or frame.size == 0:
            return self._empty_result()

        state = self._get_or_create_state(camera_id)
        state.frame_counter += 1

        # ---- pre-process ------------------------------------------------
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(
            gray,
            (self._cfg.motion_gaussian_blur_kernel,
             self._cfg.motion_gaussian_blur_kernel),
            0,
        )

        # ---- background model -------------------------------------------
        if state.background is None:
            state.background = blurred.astype(np.float32)
            return self._empty_result(state)

        # Exponential moving average: alpha=0.05 keeps background stable
        cv2.accumulateWeighted(blurred, state.background, alpha=0.05)
        background_uint8 = cv2.convertScaleAbs(state.background)

        # ---- delta + threshold ------------------------------------------
        frame_delta = cv2.absdiff(background_uint8, blurred)
        delta_mean = float(frame_delta.mean())

        _, thresh = cv2.threshold(
            frame_delta,
            self._cfg.motion_binary_threshold,
            255,
            cv2.THRESH_BINARY,
        )

        # ---- morphological cleanup --------------------------------------
        kernel = np.ones((3, 3), np.uint8)
        thresh = cv2.dilate(
            thresh,
            kernel,
            iterations=self._cfg.motion_dilate_iterations,
        )

        # ---- contour analysis -------------------------------------------
        contours, _ = cv2.findContours(
            thresh,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        significant = [
            c for c in contours
            if cv2.contourArea(c) >= self._cfg.motion_min_contour_area
        ]

        motion_detected = len(significant) > 0

        # ---- motion score (0.0 – 1.0) -----------------------------------
        # Based on the fraction of pixels changed above threshold
        total_pixels = frame.shape[0] * frame.shape[1]
        changed_pixels = int(cv2.countNonZero(thresh))
        motion_score = min(changed_pixels / max(total_pixels, 1), 1.0)

        # ---- consecutive motion tracking --------------------------------
        if motion_detected:
            state.consecutive_motion_frames += 1
        else:
            state.consecutive_motion_frames = 0

        # ---- analysis scheduling ----------------------------------------
        interval = self._cfg.analysis_interval_frames
        should_analyze = (
            motion_detected
            and (state.frame_counter % interval == 0)
        )

        result = MotionResult(
            motion_detected=motion_detected,
            motion_score=round(motion_score, 4),
            contour_count=len(significant),
            frame_delta_mean=round(delta_mean, 4),
            should_analyze=should_analyze,
        )

        if motion_detected:
            logger.debug(
                "Motion detected [cam=%s] score=%.4f contours=%d",
                camera_id,
                motion_score,
                len(significant),
            )

        return result

    def reset(self, camera_id: str = "default") -> None:
        """Clear background model for a given camera (e.g. after a scene cut)."""
        if camera_id in self._states:
            self._states[camera_id] = _FrameState()
            logger.info("MotionDetector background reset for cam=%s", camera_id)

    def draw_debug(
        self,
        frame: np.ndarray,
        result: MotionResult,
    ) -> np.ndarray:
        """
        Overlay motion information onto a copy of the frame for debugging.

        Returns the annotated frame — does NOT modify the original.
        """
        vis = frame.copy()
        color = (0, 0, 255) if result.motion_detected else (0, 255, 0)
        label = (
            f"Motion: {'YES' if result.motion_detected else 'NO'} "
            f"score={result.motion_score:.3f}"
        )
        cv2.putText(
            vis, label, (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2,
        )
        return vis

    # ------------------------------------------------------------------
    # Convenience: process a JPEG / PNG bytes payload
    # ------------------------------------------------------------------

    def process_bytes(
        self,
        image_bytes: bytes,
        camera_id: str = "default",
    ) -> Tuple[MotionResult, np.ndarray]:
        """
        Decode raw image bytes and run motion detection.

        Returns (MotionResult, decoded_frame).
        Useful for FastAPI endpoints that receive file uploads.
        """
        arr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("Could not decode image bytes — unsupported format?")
        return self.process_frame(frame, camera_id), frame

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_or_create_state(self, camera_id: str) -> _FrameState:
        if camera_id not in self._states:
            self._states[camera_id] = _FrameState()
        return self._states[camera_id]

    @staticmethod
    def _empty_result(state: Optional["_FrameState"] = None) -> MotionResult:
        return MotionResult(
            motion_detected=False,
            motion_score=0.0,
            contour_count=0,
            frame_delta_mean=0.0,
            should_analyze=False,
        )


# ---------------------------------------------------------------------------
# Module-level singleton (shared across API request handlers)
# ---------------------------------------------------------------------------

motion_detector = MotionDetector()
