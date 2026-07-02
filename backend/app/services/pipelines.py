"""Framework dispatch for extraction.

framework="pytorch" routes to the transformer pipeline in ml/pytorch_pipeline/
when its dependencies are installed; anything else (and any load failure) falls
back to the rule-based placeholder, tagged with the requested framework.
"""

import logging
import sys
from pathlib import Path

from app.config import settings
from app.schemas import ExtractionResult, Framework, ModelInfo
from app.services import extraction as rule_based

logger = logging.getLogger(__name__)

_DEFAULT_ML_DIR = Path(__file__).resolve().parents[3] / "ml"

_pytorch_inference = None  # loaded module, or None
_pytorch_error: str | None = None  # first load failure, cached so we probe once


def _load_pytorch():
    global _pytorch_inference, _pytorch_error
    if _pytorch_inference is not None or _pytorch_error is not None:
        return
    try:
        ml_dir = Path(settings.ml_dir) if settings.ml_dir else _DEFAULT_ML_DIR
        if str(ml_dir) not in sys.path:
            sys.path.insert(0, str(ml_dir))
        from pytorch_pipeline import inference  # type: ignore[import-not-found]

        if not inference.is_available():
            raise RuntimeError(
                "torch/transformers not installed — pip install -r ml/pytorch_pipeline/requirements.txt"
            )
        _pytorch_inference = inference
    except Exception as exc:
        _pytorch_error = str(exc)
        logger.warning("PyTorch pipeline unavailable, using rule-based fallback: %s", exc)


def extract(text: str, framework: Framework) -> ExtractionResult:
    if framework == "pytorch":
        _load_pytorch()
        if _pytorch_inference is not None:
            return ExtractionResult.model_validate(_pytorch_inference.extract(text))
    result = rule_based.extract(text)
    result.model_name = f"{framework}-{rule_based.MODEL_NAME}"
    return result


def model_info(framework: Framework) -> ModelInfo:
    if framework == "pytorch":
        _load_pytorch()
        if _pytorch_inference is not None:
            return ModelInfo(
                framework="pytorch",
                model_name=_pytorch_inference.model_name(),
                status="available",
                description=(
                    "Transformer NER via Hugging Face token classification (CPU). "
                    "Fine-tune with ml/pytorch_pipeline/train.py; ICD-10 suggestion is "
                    "still a dictionary placeholder."
                ),
            )
    return ModelInfo(
        framework=framework,
        model_name=f"{framework}-{rule_based.MODEL_NAME}",
        status="placeholder",
        description=(
            f"Rule-based dictionary extractor standing in for a {framework} NER model."
            + (
                f" Unavailable because: {_pytorch_error}"
                if framework == "pytorch" and _pytorch_error
                else f" Train the real one with ml/{framework}/train.py."
            )
        ),
    )
