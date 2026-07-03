"""Framework dispatch for extraction.

pytorch and tensorflow route to their pipelines under ml/ when the framework's
dependencies are installed; anything else (and any load failure) falls back to
the rule-based placeholder, tagged with the requested framework.
"""

import importlib
import logging
import sys
from threading import Lock

from app.schemas import EntityGroups, EntityOut, ExtractionResult, Framework, ModelInfo
from app.services import confidence, entity_extraction
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
FRAMEWORKS: tuple[Framework, ...] = ("pytorch", "tensorflow", "jax")
FrameworkVotes = dict[str, list[str]]


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
            return rule_based.build_result(groups, model_name=model_name, note_text=text)
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


def extract_ensemble(text: str) -> tuple[ExtractionResult, FrameworkVotes]:
    """Run available framework pipelines and merge entity votes conservatively."""
    rule_result = rule_based.extract(text)
    rule_groups = EntityGroups(
        conditions=rule_result.conditions,
        symptoms=rule_result.symptoms,
        medications=rule_result.medications,
        procedures=rule_result.procedures,
    )

    framework_groups: dict[Framework, EntityGroups] = {}
    model_names: dict[Framework, str] = {}
    votes: FrameworkVotes = {framework: [] for framework in FRAMEWORKS}

    for framework in FRAMEWORKS:
        extracted = _extract_model_groups(text, framework)
        if extracted is None:
            continue
        groups, model_name = extracted
        framework_groups[framework] = groups
        model_names[framework] = model_name
        votes[framework] = sorted(_vote_label(entity) for entity in entity_extraction.flatten_groups(groups))

    if not framework_groups:
        rule_result.model_name = f"ensemble-fallback-{rule_based.MODEL_NAME}"
        return rule_result, votes

    merged_groups = _merge_ensemble_groups(rule_groups, framework_groups)
    model_name = "ensemble:" + ",".join(
        f"{framework}={model_names[framework]}" for framework in framework_groups
    )
    return rule_based.build_result(merged_groups, model_name=model_name, note_text=text), votes


def _extract_model_groups(text: str, framework: Framework) -> tuple[EntityGroups, str] | None:
    _load(framework)
    module = _loaded.get(framework)
    if module is None:
        return None
    try:
        model_payload = module.extract(text)
        groups = entity_extraction.normalize_model_payload(text, model_payload)
        return groups, _model_name(module, model_payload)
    except (TypeError, ValueError) as exc:
        logger.warning("%s pipeline returned invalid ensemble votes: %s", framework, exc)
    except Exception as exc:
        logger.exception("%s pipeline failed during ensemble voting: %s", framework, exc)
    return None


def _merge_ensemble_groups(
    rule_groups: EntityGroups,
    framework_groups: dict[Framework, EntityGroups],
) -> EntityGroups:
    rule_entities = {
        _entity_key(entity): entity
        for entity in entity_extraction.flatten_groups(rule_groups)
    }
    framework_entities: dict[tuple[str, str], dict[Framework, EntityOut]] = {}
    for framework, groups in framework_groups.items():
        for entity in entity_extraction.flatten_groups(groups):
            framework_entities.setdefault(_entity_key(entity), {})[framework] = entity

    merged: list[EntityOut] = []
    for key in sorted(
        set(rule_entities) | set(framework_entities),
        key=lambda item: _sort_position(rule_entities.get(item), framework_entities.get(item, {})),
    ):
        merged.append(
            _ensemble_entity(
                rule_entities.get(key),
                framework_entities.get(key, {}),
                active_frameworks=tuple(framework_groups),
            )
        )
    return entity_extraction.groups_from_entities(merged)


def _ensemble_entity(
    rule_entity: EntityOut | None,
    framework_entities: dict[Framework, EntityOut],
    *,
    active_frameworks: tuple[Framework, ...],
) -> EntityOut:
    voted_entities = list(framework_entities.values())
    primary = rule_entity or max(voted_entities, key=lambda entity: entity.confidence)
    source = primary.source
    score = confidence.clamp_confidence(primary.confidence)
    warning = primary.warning

    if len(voted_entities) >= 2:
        source = "ensemble_agreement"
        score = confidence.ensemble_agreement_confidence(
            [entity.confidence for entity in voted_entities] + ([rule_entity.confidence] if rule_entity else []),
            vote_count=len(voted_entities),
        )
        warning = None
    elif len(voted_entities) == 1:
        only_framework = next(iter(framework_entities))
        only_entity = voted_entities[0]
        base_score = max(score, confidence.clamp_confidence(only_entity.confidence))
        if rule_entity is not None:
            source = "both"
        else:
            source = "model"
        if len(active_frameworks) > 1:
            missing = [framework for framework in active_frameworks if framework != only_framework]
            score = confidence.ensemble_disagreement_confidence(base_score)
            warning = (
                "Framework disagreement: "
                f"predicted by {only_framework}; not predicted by {', '.join(missing)}."
            )
        else:
            score = base_score

    return EntityOut(
        category=primary.category,
        text=primary.text,
        normalized=primary.normalized,
        span_start=primary.span_start,
        span_end=primary.span_end,
        confidence=score,
        source=source,
        warning=warning,
    )


def _entity_key(entity: EntityOut) -> tuple[str, str]:
    return (entity.category, (entity.normalized or entity.text).lower())


def _vote_label(entity: EntityOut) -> str:
    category, normalized = _entity_key(entity)
    return f"{category}:{normalized}"


def _sort_position(
    rule_entity: EntityOut | None,
    framework_entities: dict[Framework, EntityOut],
) -> tuple[int, str]:
    entity = rule_entity or next(iter(framework_entities.values()), None)
    if entity is None:
        return (10**9, "")
    return (entity.span_start if entity.span_start is not None else 10**9, entity.text.lower())


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
