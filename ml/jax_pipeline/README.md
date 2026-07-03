# jax_pipeline/

JAX/Flax research pipeline — for **benchmarking and research comparison**
against the PyTorch and TensorFlow pipelines, not production. Serves
`framework="jax"` on `/analyze-note` and `/analyze-file` when jax/flax/optax
are installed; otherwise the backend falls back to the rule-based placeholder.

## Design

An architectural twin of `tensorflow_pipeline` implemented in Flax: a
lightweight text classifier (Embed → masked mean pool → MLP softmax) predicts
the note's clinical specialty, and matched lexicon entities get a confidence
boost when they belong to the predicted specialty.

The synthetic dataset, clinical lexicon, entity finder, summarizer, and ICD
tables are **imported from `tensorflow_pipeline`** (pure-Python modules — no
TF required at runtime). The two pipelines therefore differ *only in the
model and framework*, which is the point: any metric or latency difference is
attributable to the framework/model, not the surrounding logic.

| File | Purpose |
|------|---------|
| `model.py` | Flax classifier, regex tokenizer + JSON vocab, checkpoint save/load |
| `inference.py` | `extract(text)` — classify + shared extraction + ICD suggestion |
| `train.py` | Train the classifier (optax Adam, jitted steps) on synthetic notes |
| `evaluate.py` | Category accuracy, entity P/R/F1, and ms/note latency benchmark |

## Usage

```bash
pip install -r requirements.txt   # jax, flax, optax

# from the ml/ directory:
python -m jax_pipeline.train --train-size 480 --epochs 20
python -m jax_pipeline.evaluate --size 80   # same held-out seed as TF evaluate
```

Model resolution: `MEDEXTRACT_JAX_MODEL` env var, else
`checkpoints/medextract-category-flax/`, else untrained (unboosted lexicon
extraction, reported in the model name).

## Reference benchmark (this machine, CPU)

Both classifier pipelines hit 1.000 held-out category accuracy and entity F1
on the easy synthetic set; the Flax pipeline measured ~6 ms/note end-to-end
(classify + extract) after JIT warm-up.

## Honest limitations

Same as the TensorFlow pipeline: lexicon-bound extraction, synthetic training
data, placeholder ICD lookup, no negation handling.
