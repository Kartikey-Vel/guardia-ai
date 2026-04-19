import logging
from typing import Optional

logger = logging.getLogger(__name__)

class ConfidenceScorer:
    """
    Computes a weighted confidence score by evaluating multiple input signals.
    """
    
    # Define weights for different modalities
    WEIGHTS = {
        "vision": 0.50,
        "yolo": 0.35,
        "motion": 0.15
    }

    @classmethod
    def compute_fused_confidence(
        cls,
        vision_conf: float,
        motion_score: float,
        yolo_conf: Optional[float] = None
    ) -> float:
        """
        Calculates a final unified confidence score (0.0 to 1.0).
        Automatically redistributes weights if a signal (like YOLO) is missing.
        """
        active_weights = {
            "vision": cls.WEIGHTS["vision"],
            "motion": cls.WEIGHTS["motion"]
        }
        
        if yolo_conf is not None and yolo_conf > 0:
            active_weights["yolo"] = cls.WEIGHTS["yolo"]
            
        # Normalize weights so they sum to 1.0
        total_weight = sum(active_weights.values())
        normalized_weights = {k: v / total_weight for k, v in active_weights.items()}
        
        # Calculate weighted sum
        # Note: Motion score is typically lower, so we scale it up slightly for confidence purposes
        scaled_motion = min(motion_score * 1.5, 1.0)
        
        score = (vision_conf * normalized_weights["vision"]) + (scaled_motion * normalized_weights["motion"])
        
        if "yolo" in normalized_weights and yolo_conf is not None:
            score += (yolo_conf * normalized_weights["yolo"])
            
        return round(max(0.0, min(1.0, score)), 4)

# Singleton instance
confidence_scorer = ConfidenceScorer()
