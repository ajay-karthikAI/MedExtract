from app.schemas import EntityOut, ExtractionResult, Icd10Out
from app.services import calibration


def test_confidence_bucket_labels_cover_requested_ranges():
    assert calibration.bucket_label(0.0) == "0-25"
    assert calibration.bucket_label(0.25) == "0-25"
    assert calibration.bucket_label(0.26) == "26-50"
    assert calibration.bucket_label(0.5) == "26-50"
    assert calibration.bucket_label(0.51) == "51-75"
    assert calibration.bucket_label(0.75) == "51-75"
    assert calibration.bucket_label(0.76) == "76-100"
    assert calibration.bucket_label(1.0) == "76-100"


def test_collect_predictions_marks_correctness_from_ground_truth():
    note = {
        "ground_truth": {
            "conditions": ["hypertension"],
            "symptoms": [],
            "medications": [],
            "procedures": [],
            "icd10_codes": ["I10"],
        }
    }
    result = ExtractionResult(
        conditions=[
            EntityOut(category="condition", text="HTN", normalized="hypertension", confidence=0.9),
            EntityOut(category="condition", text="asthma", normalized="asthma", confidence=0.7),
        ],
        icd10_suggestions=[
            Icd10Out(code="I10", description="Essential hypertension", confidence=0.8),
            Icd10Out(code="J45.909", description="Asthma", confidence=0.6),
        ],
    )

    predictions = calibration.collect_predictions(note, result)

    assert [(prediction.label, prediction.correct) for prediction in predictions] == [
        ("conditions:hypertension", True),
        ("conditions:asthma", False),
        ("icd10:I10", True),
        ("icd10:J45.909", False),
    ]


def test_calibration_report_calculates_accuracy_per_bucket():
    report = calibration.calibration_report(
        [
            calibration.CalibrationPrediction(kind="entity", label="a", confidence=0.2, correct=False),
            calibration.CalibrationPrediction(kind="entity", label="b", confidence=0.4, correct=True),
            calibration.CalibrationPrediction(kind="entity", label="c", confidence=0.6, correct=False),
            calibration.CalibrationPrediction(kind="icd10", label="d", confidence=0.9, correct=True),
            calibration.CalibrationPrediction(kind="icd10", label="e", confidence=0.95, correct=True),
        ]
    )

    assert [bucket["bucket"] for bucket in report["curve"]] == ["0-25", "26-50", "51-75", "76-100"]
    assert report["curve"][0]["accuracy"] == 0.0
    assert report["curve"][1]["accuracy"] == 1.0
    assert report["curve"][2]["accuracy"] == 0.0
    assert report["curve"][3]["accuracy"] == 1.0
    assert report["total_predictions"] == 5
    assert report["expected_calibration_error"] > 0
