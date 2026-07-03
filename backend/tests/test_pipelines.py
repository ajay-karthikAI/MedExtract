from app.services import pipelines


class _FakeModelModule:
    def extract(self, text: str) -> dict:
        return {
            "conditions": [
                {
                    "category": "condition",
                    "text": "hypertension",
                    "normalized": "hypertension",
                    "span_start": text.index("hypertension"),
                    "span_end": text.index("hypertension") + len("hypertension"),
                    "confidence": 0.9,
                }
            ],
            "symptoms": [],
            "medications": [],
            "procedures": [],
            "icd10_suggestions": [{"code": 123, "not_the_contract": True}],
            "patient_summary": "Bogus model summary.",
            "model_name": "fake-model",
        }


class _FailingModelModule:
    def extract(self, _: str) -> dict:
        raise RuntimeError("model crashed")


def test_pipeline_rebuilds_non_entity_outputs(monkeypatch):
    monkeypatch.setattr(pipelines, "_load", lambda framework: None)
    monkeypatch.setattr(pipelines, "_loaded", {"pytorch": _FakeModelModule()})

    result = pipelines.extract("Patient has hypertension.", "pytorch")

    assert result.model_name == "fake-model"
    assert [suggestion.code for suggestion in result.icd10_suggestions] == ["I10"]
    assert result.patient_summary != "Bogus model summary."


def test_pipeline_falls_back_when_model_runtime_fails(monkeypatch):
    monkeypatch.setattr(pipelines, "_load", lambda framework: None)
    monkeypatch.setattr(pipelines, "_loaded", {"pytorch": _FailingModelModule()})

    result = pipelines.extract("Patient has hypertension.", "pytorch")

    assert result.model_name == "pytorch-rule-based-v0"
    assert {entity.normalized for entity in result.conditions} == {"hypertension"}
