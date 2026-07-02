from app.services.extraction import extract

NOTE = (
    "Patient reports chest pain and shortness of breath for two days. "
    "History of hypertension and type 2 diabetes. "
    "Continue lisinopril 10mg daily and metformin 500mg BID. "
    "ECG and chest x-ray ordered."
)


def test_extracts_all_categories():
    result = extract(NOTE)
    assert {e.normalized for e in result.symptoms} == {"chest pain", "dyspnea"}
    assert {e.normalized for e in result.conditions} == {
        "hypertension",
        "type 2 diabetes mellitus",
    }
    assert {e.normalized for e in result.medications} == {"lisinopril", "metformin"}
    assert {e.normalized for e in result.procedures} == {
        "electrocardiogram",
        "chest radiograph",
    }


def test_icd10_suggestions_include_condition_codes():
    codes = {s.code for s in extract(NOTE).icd10_suggestions}
    assert "I10" in codes
    assert "E11.9" in codes


def test_longest_match_wins():
    result = extract("Dx: type 2 diabetes.")
    assert [e.normalized for e in result.conditions] == ["type 2 diabetes mellitus"]


def test_summary_is_plain_english():
    summary = extract(NOTE).patient_summary
    assert "chest pain" in summary
    assert "not medical advice" in summary


def test_empty_findings_still_returns_summary():
    result = extract("Administrative note: rescheduled appointment.")
    assert result.conditions == []
    assert result.patient_summary  # non-empty fallback message


def test_spans_point_into_source_text():
    result = extract(NOTE)
    for entity in result.symptoms + result.conditions:
        assert NOTE[entity.span_start : entity.span_end].lower() == entity.text.lower()
