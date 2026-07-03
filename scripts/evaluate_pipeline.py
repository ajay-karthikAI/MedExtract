#!/usr/bin/env python3
"""Evaluate MedExtract extraction quality against data/eval_notes.json."""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path
from statistics import mean
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

warnings.filterwarnings(
    "ignore",
    message='Field "model_.*" has conflict with protected namespace "model_".*',
    category=UserWarning,
)

from app.schemas import ExtractionResult  # noqa: E402
from app.services import calibration, confidence, entity_extraction, extraction, pipelines  # noqa: E402

ENTITY_FIELDS = ("conditions", "symptoms", "medications", "procedures")
FRAMEWORKS = ("rule", "pytorch", "tensorflow", "jax")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate MedExtract on a labeled synthetic dataset.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=REPO_ROOT / "data" / "eval_notes.json",
        help="Path to the evaluation dataset JSON file.",
    )
    parser.add_argument(
        "--framework",
        choices=FRAMEWORKS,
        default="rule",
        help="Pipeline to evaluate. 'rule' uses the deterministic backend extractor.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON metrics.",
    )
    parser.add_argument(
        "--show-errors",
        action="store_true",
        help="Print per-note false positives and false negatives.",
    )
    return parser.parse_args()


def normalize_label(value: object) -> str:
    return " ".join(str(value).strip().lower().split())


def entity_key(category: str, value: object) -> str:
    return f"{category}:{normalize_label(value)}"


def safe_divide(numerator: int | float, denominator: int | float) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


def prf(tp: int, fp: int, fn: int) -> dict[str, float]:
    precision = safe_divide(tp, tp + fp)
    recall = safe_divide(tp, tp + fn)
    f1 = safe_divide(2 * precision * recall, precision + recall)
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def ground_truth_entities(note: dict[str, Any]) -> set[str]:
    truth = note.get("ground_truth", {})
    labels: set[str] = set()
    for field in ENTITY_FIELDS:
        for value in truth.get(field, []):
            labels.add(entity_key(field, value))
    return labels


def predicted_entities(result: ExtractionResult) -> set[str]:
    labels: set[str] = set()
    for field in ENTITY_FIELDS:
        for entity in getattr(result, field):
            labels.add(entity_key(field, entity.normalized or entity.text))
    return labels


def ground_truth_icd_codes(note: dict[str, Any]) -> set[str]:
    truth = note.get("ground_truth", {})
    return {normalize_label(code).upper() for code in truth.get("icd10_codes", [])}


def predicted_icd_codes(result: ExtractionResult) -> set[str]:
    return {normalize_label(code.code).upper() for code in result.icd10_suggestions}


def extract_note(text: str, framework: str) -> ExtractionResult:
    if framework == "rule":
        return extraction.extract(text)
    return pipelines.extract(text, framework)  # type: ignore[arg-type]


def note_confidence(result: ExtractionResult) -> float:
    entities = entity_extraction.flatten_groups(
        entity_extraction.groups_from_entities(
            result.conditions + result.symptoms + result.medications + result.procedures
        )
    )
    return confidence.overall_confidence(entities, result.icd10_suggestions)


def evaluate(notes: list[dict[str, Any]], framework: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    entity_tp = entity_fp = entity_fn = 0
    icd_tp = icd_fp = icd_fn = 0
    exact_icd_matches = 0
    note_confidences: list[float] = []
    calibration_predictions: list[calibration.CalibrationPrediction] = []
    errors: list[dict[str, Any]] = []
    by_category = {
        field: {"tp": 0, "fp": 0, "fn": 0}
        for field in ENTITY_FIELDS
    }

    for note in notes:
        result = extract_note(str(note["note"]), framework)
        expected_entities = ground_truth_entities(note)
        actual_entities = predicted_entities(result)
        expected_codes = ground_truth_icd_codes(note)
        actual_codes = predicted_icd_codes(result)

        tp_entities = expected_entities & actual_entities
        fp_entities = actual_entities - expected_entities
        fn_entities = expected_entities - actual_entities
        entity_tp += len(tp_entities)
        entity_fp += len(fp_entities)
        entity_fn += len(fn_entities)

        for field in ENTITY_FIELDS:
            prefix = f"{field}:"
            expected_for_field = {item for item in expected_entities if item.startswith(prefix)}
            actual_for_field = {item for item in actual_entities if item.startswith(prefix)}
            by_category[field]["tp"] += len(expected_for_field & actual_for_field)
            by_category[field]["fp"] += len(actual_for_field - expected_for_field)
            by_category[field]["fn"] += len(expected_for_field - actual_for_field)

        tp_codes = expected_codes & actual_codes
        fp_codes = actual_codes - expected_codes
        fn_codes = expected_codes - actual_codes
        icd_tp += len(tp_codes)
        icd_fp += len(fp_codes)
        icd_fn += len(fn_codes)
        if expected_codes == actual_codes:
            exact_icd_matches += 1

        note_confidences.append(note_confidence(result))
        calibration_predictions.extend(calibration.collect_predictions(note, result))

        if fp_entities or fn_entities or fp_codes or fn_codes:
            errors.append(
                {
                    "id": note.get("id"),
                    "false_positive_entities": sorted(fp_entities),
                    "false_negative_entities": sorted(fn_entities),
                    "false_positive_icd_codes": sorted(fp_codes),
                    "false_negative_icd_codes": sorted(fn_codes),
                }
            )

    entity_metrics = prf(entity_tp, entity_fp, entity_fn)
    icd_metrics = prf(icd_tp, icd_fp, icd_fn)
    metrics = {
        "framework": framework,
        "notes": len(notes),
        "precision": entity_metrics["precision"],
        "recall": entity_metrics["recall"],
        "f1": entity_metrics["f1"],
        "icd_accuracy": round(safe_divide(exact_icd_matches, len(notes)), 4),
        "icd_precision": icd_metrics["precision"],
        "icd_recall": icd_metrics["recall"],
        "icd_f1": icd_metrics["f1"],
        "average_confidence": round(mean(note_confidences), 4) if note_confidences else 0.0,
        "entity_counts": {
            "true_positive": entity_tp,
            "false_positive": entity_fp,
            "false_negative": entity_fn,
        },
        "icd_counts": {
            "true_positive": icd_tp,
            "false_positive": icd_fp,
            "false_negative": icd_fn,
            "exact_match_notes": exact_icd_matches,
        },
        "by_category": {
            field: prf(counts["tp"], counts["fp"], counts["fn"])
            for field, counts in by_category.items()
        },
        "calibration": calibration.calibration_report(calibration_predictions),
    }
    return metrics, errors


def load_dataset(path: Path) -> list[dict[str, Any]]:
    notes = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(notes, list):
        raise ValueError("Evaluation dataset must be a JSON list")
    if len(notes) < 50:
        raise ValueError(f"Evaluation dataset must include at least 50 notes; found {len(notes)}")
    for index, note in enumerate(notes, start=1):
        if not isinstance(note, dict) or "note" not in note or "ground_truth" not in note:
            raise ValueError(f"Invalid dataset item at index {index}")
    return notes


def print_report(metrics: dict[str, Any], errors: list[dict[str, Any]], *, show_errors: bool) -> None:
    print("MedExtract evaluation")
    print(f"Framework: {metrics['framework']}")
    print(f"Notes: {metrics['notes']}")
    print(f"Precision: {metrics['precision']:.4f}")
    print(f"Recall: {metrics['recall']:.4f}")
    print(f"F1 score: {metrics['f1']:.4f}")
    print(f"ICD accuracy: {metrics['icd_accuracy']:.4f}")
    print(f"Average confidence: {metrics['average_confidence']:.4f}")
    print()
    print("ICD detail")
    print(f"Precision: {metrics['icd_precision']:.4f}")
    print(f"Recall: {metrics['icd_recall']:.4f}")
    print(f"F1 score: {metrics['icd_f1']:.4f}")
    print()
    print("Entity detail")
    for field in ENTITY_FIELDS:
        scores = metrics["by_category"][field]
        print(f"{field}: precision={scores['precision']:.4f} recall={scores['recall']:.4f} f1={scores['f1']:.4f}")

    print()
    print("Confidence calibration")
    print(f"Expected calibration error: {metrics['calibration']['expected_calibration_error']:.4f}")
    for bucket in metrics["calibration"]["curve"]:
        print(
            f"{bucket['bucket']}%: "
            f"n={bucket['count']} "
            f"accuracy={bucket['accuracy']:.4f} "
            f"avg_confidence={bucket['average_confidence']:.4f} "
            f"gap={bucket['calibration_gap']:.4f}"
        )

    if show_errors and errors:
        print()
        print("Errors")
        for error in errors:
            print(json.dumps(error, sort_keys=True))


def main() -> int:
    args = parse_args()
    notes = load_dataset(args.dataset)
    metrics, errors = evaluate(notes, args.framework)
    if args.json:
        print(json.dumps({"metrics": metrics, "errors": errors}, indent=2, sort_keys=True))
    else:
        print_report(metrics, errors, show_errors=args.show_errors)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
