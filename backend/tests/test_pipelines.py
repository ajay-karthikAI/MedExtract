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


class _StaticModelModule:
    def __init__(self, name: str, conditions: list[str]):
        self.name = name
        self.conditions = conditions

    def extract(self, text: str) -> dict:
        return {
            "conditions": [
                {
                    "category": "condition",
                    "text": condition,
                    "normalized": condition,
                    "span_start": text.index(condition),
                    "span_end": text.index(condition) + len(condition),
                    "confidence": 0.82,
                }
                for condition in self.conditions
            ],
            "symptoms": [],
            "medications": [],
            "procedures": [],
            "model_name": self.name,
        }


def test_pipeline_rebuilds_non_entity_outputs(monkeypatch):
    monkeypatch.setattr(pipelines, "_load", lambda framework: None)
    monkeypatch.setattr(pipelines, "_loaded", {"pytorch": _FakeModelModule()})

    result = pipelines.extract("Patient has hypertension.", "pytorch")

    assert result.model_name == "fake-model"
    assert [suggestion.code for suggestion in result.icd10_suggestions] == ["I10"]
    assert result.patient_summary != "Bogus model summary."
    assert result.conditions[0].source == "both"
    assert result.conditions[0].confidence > 0.9


def test_pipeline_falls_back_when_model_runtime_fails(monkeypatch):
    monkeypatch.setattr(pipelines, "_load", lambda framework: None)
    monkeypatch.setattr(pipelines, "_loaded", {"pytorch": _FailingModelModule()})

    result = pipelines.extract("Patient has hypertension.", "pytorch")

    assert result.model_name == "pytorch-rule-based-v0"
    assert {entity.normalized for entity in result.conditions} == {"hypertension"}
    assert {entity.source for entity in result.conditions} == {"rule"}


def test_ensemble_marks_framework_agreement_and_disagreement(monkeypatch):
    monkeypatch.setattr(pipelines, "_load", lambda framework: None)
    monkeypatch.setattr(
        pipelines,
        "_loaded",
        {
            "pytorch": _StaticModelModule("fake-pytorch", ["hypertension"]),
            "tensorflow": _StaticModelModule("fake-tensorflow", ["hypertension"]),
            "jax": _StaticModelModule("fake-jax", ["asthma"]),
        },
    )

    result, votes = pipelines.extract_ensemble("Patient has hypertension and asthma.")

    assert votes == {
        "pytorch": ["condition:hypertension"],
        "tensorflow": ["condition:hypertension"],
        "jax": ["condition:asthma"],
    }
    entities = {entity.normalized: entity for entity in result.conditions}
    assert entities["hypertension"].source == "ensemble_agreement"
    assert entities["hypertension"].warning is None
    assert entities["hypertension"].confidence > 0.82
    assert entities["asthma"].source == "both"
    assert entities["asthma"].confidence < 0.82
    assert entities["asthma"].warning
    assert "not predicted by pytorch, tensorflow" in entities["asthma"].warning


def test_ensemble_falls_back_without_framework_votes(monkeypatch):
    monkeypatch.setattr(pipelines, "_load", lambda framework: None)
    monkeypatch.setattr(pipelines, "_loaded", {})

    result, votes = pipelines.extract_ensemble("Patient has hypertension.")

    assert votes == {"pytorch": [], "tensorflow": [], "jax": []}
    assert result.model_name == "ensemble-fallback-rule-based-v0"
    assert result.conditions[0].source == "rule"
