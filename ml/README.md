# ml/

Framework-specific skeletons for training clinical NER models. Each subfolder is
independent — install only the framework you're working with.

| Folder              | Framework   | Status                                        |
|---------------------|-------------|-----------------------------------------------|
| `pytorch_pipeline/` | PyTorch     | **Working pipeline** — HF Transformers NER, serves `framework="pytorch"` |
| `pytorch/`          | PyTorch     | training skeleton                             |
| `tensorflow/`       | TensorFlow  | training skeleton                             |
| `jax/`              | JAX / Flax  | training skeleton                             |

## Contract with the backend

A trained model becomes usable by the API by implementing the same interface as
the placeholder in `backend/app/services/extraction.py`:

```python
def extract(text: str) -> ExtractionResult: ...
```

Entity labels: `condition`, `symptom`, `medication`, `procedure` (BIO-tagged for
token classification).

## Data policy

Train **only** on synthetic or properly licensed, de-identified datasets.
Never place real patient data (PHI) in this repository. `data/sample_notes/`
holds synthetic examples for smoke-testing pipelines.
