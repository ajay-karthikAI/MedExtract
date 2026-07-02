# pytorch_pipeline/

PyTorch clinical NLP pipeline (Hugging Face Transformers). Serves
`framework="pytorch"` requests on `/analyze-note` and `/analyze-file` when its
dependencies are installed; otherwise the backend falls back to the rule-based
placeholder automatically.

| File | Purpose |
|------|---------|
| `model.py` | NER model loading, label→category mapping, ICD-10 suggester (placeholder), confidence helpers |
| `inference.py` | `extract(text)` — NER + post-processing + ICD codes + patient summary |
| `train.py` | Fine-tune a token-classification model on synthetic BIO-tagged notes |
| `evaluate.py` | Span-level precision/recall/F1 on held-out synthetic notes |
| `synthetic.py` | Synthetic note generator with gold entity spans (no real data) |

## Model resolution (in order)

1. `MEDEXTRACT_PT_MODEL` env var (any HF hub id or local path)
2. `checkpoints/medextract-ner/` if present (produced by `train.py`)
3. `d4data/biomedical-ner-all` — small pretrained biomedical NER (DistilBERT,
   MACCROBAT labels). Good on narrative prose; weak on terse section lists
   like `PMH: …`, which is what fine-tuning fixes.

## Usage

```bash
pip install -r requirements.txt   # torch + transformers

# from the ml/ directory:
python -m pytorch_pipeline.train --train-size 300 --epochs 3
python -m pytorch_pipeline.evaluate --size 50
```

The backend picks the pipeline up with no configuration as long as torch and
transformers are importable in the API process (run the backend from a venv
with `ml/pytorch_pipeline/requirements.txt` installed — the slim Docker image
deliberately excludes them).

## Honest limitations

- ICD-10 "classification" is a dictionary lookup scaled by NER confidence —
  a placeholder for a real classification head.
- Fine-tuned on templated synthetic notes; expect template-shaped competence.
- No negation handling ("denies fever" still yields *fever*).
- Normalization is lowercasing, not UMLS/SNOMED linking.
