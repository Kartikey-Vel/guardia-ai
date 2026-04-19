"""
Fusion Controller — Public Re-export
======================================
Thin wrapper that exposes a unified `FusionController` class combining
Groq LLM fusion (primary) and heuristic fallback (secondary).
The heavy implementation lives in groq_fusion.py; this file aligns with
the module name referenced in the README and pipeline imports.
"""

from ai.groq_fusion import GroqFusionController, groq_fusion  # noqa: F401

# Alias for callers that import `fusion_controller.fusion_controller`
FusionController = GroqFusionController
fusion_controller = groq_fusion
