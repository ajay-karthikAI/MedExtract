"""Framework dispatch for extraction.

pytorch and tensorflow route to their pipelines under ml/ when the framework's
dependencies are installed; anything else (and any load failure) falls back to
the rule-based placeholder, tagged with the requested framework.
"""

import importlib
import logging
import sys
from pathlib import Path

from app.config import settings
from app.schemas import ExtractionResult, Framework, ModelInfo
from app.services import extraction as rule_based

logger = logging.getLogger(__name__)

_DEFAULT_ML_DIR = Path(__file__).resolve().parents[3] / "ml"

# framework -> (inference module under ml/, description when available)
_ML_PIPELINES: dict[str, tuple[str, str]] = {
    "pytorch": (
        "pytorch_pipeline.inference",
        "Transformer NER via Hugging Face token classification (CPU). "
        "Fine-tune with ml/pytorch_pipeline/train.py; ICD-10 suggestion is "
        "still a dictionary placeholder.",
    ),
    "tensorflow": (
        "tensorflow_pipeline.inference",
        "Keras note-category classifier + lexicon entity extraction with "
        "model-assisted confidence. Train with ml/tensorflow_pipeline/train.py; "
        "ICD-10 suggestion is still a dictionary placeholder.",
    ),
    "jax": (
        "jax_pipeline.inference",
        "Flax note-category classifier + shared lexicon extraction — research/"
        "benchmarking twin of the TensorFlow pipeline. Train with "
        "ml/jax_pipeline/train.py; not intended for production.",
    ),
}

_loaded: dict[str, object] = {}  # framework -> inference module
_errors: dict[str, str] = {}  # framework -> first load failure (probed once)


def _load(framework: str) -> None:
    if framework in _loaded or framework in _errors or framework not in _ML_PIPELINES:
        return
    module_path, _ = _ML_PIPELINES[framework]
    try:
        ml_dir = Path(settings.ml_dir) if settings.ml_dir else _DEFAULT_ML_DIR
        if str(ml_dir) not in sys.path:
            sys.path.insert(0, str(ml_dir))
        module = importlib.import_module(module_path)
        if not module.is_available():
            package = module_path.split(".")[0]
            raise RuntimeError(
                f"ML dependencies not installed — pip install -r ml/{package}/requirements.txt"
            )
        _loaded[framework] = module
    except Exception as exc:
        _errors[framework] = str(exc)
        logger.warning(
            "%s pipeline unavailable, using rule-based fallback: %s", framework, exc
        )


def extract(text: str, framework: Framework) -> ExtractionResult:
    _load(framework)
    module = _loaded.get(framework)
    if module is not None:
        return ExtractionResult.model_validate(module.extract(text))
    result = rule_based.extract(text)
    result.model_name = f"{framework}-{rule_based.MODEL_NAME}"
    return result


def model_info(framework: Framework) -> ModelInfo:
    _load(framework)
    module = _loaded.get(framework)
    if module is not None:
        return ModelInfo(
            framework=framework,
            model_name=module.model_name(),
            status="available",
            description=_ML_PIPELINES[framework][1],
        )
    reason = (
        f" Unavailable because: {_errors[framework]}"
        if framework in _errors
        else f" A training skeleton lives at ml/skeletons/{framework}/train.py."
    )
    return ModelInfo(
        framework=framework,
        model_name=f"{framework}-{rule_based.MODEL_NAME}",
        status="placeholder",
        description=f"Rule-based dictionary extractor standing in for a {framework} NER model.{reason}",
    )
