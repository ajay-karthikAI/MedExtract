"""Confidence calibration reporting for MedExtract predictions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.schemas import ExtractionResult
from app.services.confidence import clamp_confidence

ENTITY_FIELDS = ("conditions", "symptoms", "medications", "procedures")
BUCKET_LABELS = ("0-25", "26-50", "51-75", "76-100")


@dataclass(frozen=True)
class CalibrationPrediction:
    kind: str
    label: str
    confidence: float
    correct: bool


def normalize_label(value: object) -> str:
    return " ".join(str(value).strip().lower().split())


def entity_key(category: str, value: object) -> str:
    return f"{category}:{normalize_label(value)}"


def bucket_label(confidence: float) -> str:
    percent = round(clamp_confidence(confidence) * 100)
    if percent <= 25:
        return "0-25"
    if percent <= 50:
        return "26-50"
    if percent <= 75:
        return "51-75"
    return "76-100"


def collect_predictions(note: dict[str, Any], result: ExtractionResult) -> list[CalibrationPrediction]:
    truth = note.get("ground_truth", {})
    expected_entities = {
        entity_key(field, value)
        for field in ENTITY_FIELDS
        for value in truth.get(field, [])
    }
    expected_codes = {
        normalize_label(code).upper()
        for code in truth.get("icd10_codes", [])
    }

    predictions: list[CalibrationPrediction] = []
    for field in ENTITY_FIELDS:
        for entity in getattr(result, field):
            key = entity_key(field, entity.normalized or entity.text)
            predictions.append(
                CalibrationPrediction(
                    kind="entity",
                    label=key,
                    confidence=clamp_confidence(entity.confidence),
                    correct=key in expected_entities,
                )
            )

    for code in result.icd10_suggestions:
        key = normalize_label(code.code).upper()
        predictions.append(
            CalibrationPrediction(
                kind="icd10",
                label=f"icd10:{key}",
                confidence=clamp_confidence(code.confidence),
                correct=key in expected_codes,
            )
        )

    return predictions


def calibration_report(predictions: list[CalibrationPrediction]) -> dict[str, Any]:
    buckets = []
    total_predictions = len(predictions)
    expected_calibration_error = 0.0

    for label in BUCKET_LABELS:
        bucket_predictions = [
            prediction
            for prediction in predictions
            if bucket_label(prediction.confidence) == label
        ]
        count = len(bucket_predictions)
        correct = sum(1 for prediction in bucket_predictions if prediction.correct)
        avg_confidence = (
            sum(prediction.confidence for prediction in bucket_predictions) / count
            if count
            else 0.0
        )
        accuracy = correct / count if count else 0.0
        calibration_gap = accuracy - avg_confidence
        if total_predictions:
            expected_calibration_error += (count / total_predictions) * abs(calibration_gap)

        buckets.append(
            {
                "bucket": label,
                "count": count,
                "correct": correct,
                "accuracy": round(accuracy, 4),
                "average_confidence": round(avg_confidence, 4),
                "calibration_gap": round(calibration_gap, 4),
            }
        )

    return {
        "total_predictions": total_predictions,
        "curve": buckets,
        "expected_calibration_error": round(expected_calibration_error, 4),
    }
