"""Framework dispatch for extraction.

pytorch and tensorflow route to their pipelines under ml/ when the framework's
dependencies are installed; anything else (and any load failure) falls back to
the rule-based placeholder, tagged with the requested framework.
"""

import importlib
import logging
import sys
from threading import Lock

from app.schemas import ExtractionResult, Framework, ModelInfo
from app.services import entity_extraction
from app.services import extraction as rule_based
from app.services.paths import ml_dir as resolve_ml_dir

logger = logging.getLogger(__name__)

# framework -> (inference module under ml/, description when available)
_ML_PIPELINES: dict[str, tuple[str, str]] = {
    "pytorch": (
        "pytorch_pipeline.inference",
        "Transformer NER via Hugging Face token classification (CPU). "
        "Fine-tune with ml/pytorch_pipeline/train.py; backend services rebuild "
        "ICD-10 suggestions, summaries, and confidence from entity evidence.",
    ),
    "tensorflow": (
        "tensorflow_pipeline.inference",
        "Keras note-category classifier + lexicon entity extraction with "
        "model-assisted confidence. Train with ml/tensorflow_pipeline/train.py; "
        "backend services rebuild ICD-10 suggestions and summaries from entity evidence.",
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
_load_lock = Lock()


def _load(framework: str) -> None:
    if framework in _loaded or framework in _errors or framework not in _ML_PIPELINES:
        return
    with _load_lock:
        if framework in _loaded or framework in _errors or framework not in _ML_PIPELINES:
            return
        module_path, _ = _ML_PIPELINES[framework]
        try:
            ml_dir = resolve_ml_dir()
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
        try:
            model_payload = module.extract(text)
            groups = entity_extraction.extract_with_model_payload(text, model_payload)
            model_name = _model_name(module, model_payload)
            return rule_based.build_result(groups, model_name=model_name)
        except (TypeError, ValueError) as exc:
            logger.warning(
                "%s pipeline returned an invalid result, using rule-based fallback: %s",
                framework,
                exc,
            )
        except Exception as exc:
            logger.exception(
                "%s pipeline failed during extraction, using rule-based fallback: %s",
                framework,
                exc,
            )
    result = rule_based.extract(text)
    result.model_name = f"{framework}-{rule_based.MODEL_NAME}"
    return result


def _model_name(module: object, model_payload: object) -> str:
    if isinstance(model_payload, dict):
        payload_name = model_payload.get("model_name")
    else:
        payload_name = getattr(model_payload, "model_name", None)
    if payload_name and payload_name != rule_based.MODEL_NAME:
        return str(payload_name)
    model_name = getattr(module, "model_name", None)
    if callable(model_name):
        try:
            return str(model_name())
        except Exception:
            logger.exception("Could not read model name from loaded pipeline")
    return rule_based.MODEL_NAME


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
        description=f"Rule-based dictionary extractor standing in for the {framework} pipeline.{reason}",
    )
