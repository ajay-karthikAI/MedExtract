# tensorflow_pipeline/

TensorFlow/Keras clinical NLP pipeline. Serves `framework="tensorflow"`
requests on `/analyze-note` and `/analyze-file` when TensorFlow is installed;
otherwise the backend falls back to the rule-based placeholder automatically.
API output is identical in shape to the PyTorch pipeline's.

## Design

Instead of token-level NER (the PyTorch pipeline's approach), this pipeline is
classifier-assisted lexicon extraction:

1. **Tokenize + classify** — a small Keras model (TextVectorization →
   Embedding → pooling → softmax) predicts the note's clinical specialty
   (cardiovascular, respiratory, endocrine, …). Tokenization lives inside the
   saved model, so the `.keras` checkpoint is self-contained.
2. **Extract entities** — lightweight longest-match-first lexicon search over
   specialty-organized clinical terms.
3. **Model-assisted confidence** — a matched entity that belongs to the
   predicted specialty gets `0.55 + 0.35 × P(specialty)`; off-category matches
   stay at the 0.55 base.
4. **ICD-10 suggestions** — dictionary-lookup placeholder scaled by entity
   confidence (same contract as the PyTorch pipeline).

| File | Purpose |
|------|---------|
| `model.py` | Keras classifier builder/loader, entity lexicon, ICD suggester |
| `inference.py` | `extract(text)` — classify + extract + suggest |
| `train.py` | Train the note-category classifier on synthetic labeled notes |
| `evaluate.py` | Category accuracy + span-level entity P/R/F1 on held-out data |
| `synthetic.py` | Specialty-labeled synthetic note generator (no real data) |

## Usage

```bash
pip install -r requirements.txt   # tensorflow

# from the ml/ directory:
python -m tensorflow_pipeline.train --train-size 480 --epochs 12
python -m tensorflow_pipeline.evaluate --size 80
```

Model resolution: `MEDEXTRACT_TF_MODEL` env var, else
`checkpoints/medextract-category.keras`, else untrained (extraction still
works, just without the confidence boost — reported in the model name).

## Honest limitations

- Entity extraction is a lexicon, not a learned tagger — unseen terms are
  invisible; the model only adjusts confidence, it doesn't find entities.
- The classifier is trained on templated synthetic notes (8 specialties).
- ICD-10 suggestion is a dictionary lookup, not a classification head.
- No negation handling ("denies fever" still yields *fever*).
