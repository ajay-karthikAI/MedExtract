"""Model layer for the JAX/Flax research pipeline.

A lightweight Flax text classifier (Embed -> masked mean pool -> MLP softmax)
that predicts a note's clinical specialty — architecturally equivalent to the
TensorFlow pipeline's Keras model so the two can be benchmarked against each
other. Tokenization is a plain regex word tokenizer with a JSON-persisted
vocabulary (JAX has no TextVectorization equivalent).

The clinical lexicon, specialties, ICD tables, and synthetic dataset are
deliberately *shared* with tensorflow_pipeline (pure-Python imports, no TF
needed) so research comparisons are apples-to-apples.
"""

import json
import os
import re
from pathlib import Path

from tensorflow_pipeline.synthetic import CATEGORIES

CHECKPOINT_DIR = Path(__file__).resolve().parent / "checkpoints" / "medextract-category-flax"

PAD_ID = 0
UNK_ID = 1
_WORD = re.compile(r"[a-z0-9']+")

EMBED_DIM = 64
HIDDEN_DIM = 64
SEQ_LEN = 160
MAX_VOCAB = 6000


def resolve_model_dir() -> Path:
    override = os.environ.get("MEDEXTRACT_JAX_MODEL")
    return Path(override) if override else CHECKPOINT_DIR


def build_vocab(texts: list[str], max_tokens: int = MAX_VOCAB) -> dict[str, int]:
    counts: dict[str, int] = {}
    for text in texts:
        for word in _WORD.findall(text.lower()):
            counts[word] = counts.get(word, 0) + 1
    ranked = sorted(counts, key=lambda w: (-counts[w], w))[: max_tokens - 2]
    return {word: i + 2 for i, word in enumerate(ranked)}  # 0=PAD, 1=UNK


def tokenize(text: str, vocab: dict[str, int], seq_len: int = SEQ_LEN) -> list[int]:
    ids = [vocab.get(w, UNK_ID) for w in _WORD.findall(text.lower())][:seq_len]
    return ids + [PAD_ID] * (seq_len - len(ids))


def build_classifier(vocab_size: int):
    """Flax module; heavy imports stay lazy so this file imports without jax."""
    import flax.linen as nn
    import jax.numpy as jnp

    class CategoryClassifier(nn.Module):
        @nn.compact
        def __call__(self, ids):  # ids: (batch, seq_len) int32
            mask = (ids != PAD_ID)[..., None]
            x = nn.Embed(num_embeddings=vocab_size, features=EMBED_DIM)(ids)
            x = (x * mask).sum(axis=1) / jnp.clip(mask.sum(axis=1), 1, None)
            x = nn.relu(nn.Dense(HIDDEN_DIM)(x))
            return nn.Dense(len(CATEGORIES))(x)  # logits

    return CategoryClassifier()


def save_checkpoint(params, vocab: dict[str, int], out_dir: Path) -> None:
    from flax.serialization import to_bytes

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "params.msgpack").write_bytes(to_bytes(params))
    (out_dir / "config.json").write_text(
        json.dumps({"vocab": vocab, "seq_len": SEQ_LEN, "categories": CATEGORIES})
    )


def load_checkpoint():
    """(model, params, vocab) from the checkpoint dir, or None if absent."""
    path = resolve_model_dir()
    if not (path / "config.json").exists():
        return None
    import jax
    import jax.numpy as jnp
    from flax.serialization import from_bytes

    config = json.loads((path / "config.json").read_text())
    vocab = config["vocab"]
    model = build_classifier(vocab_size=len(vocab) + 2)
    template = model.init(
        jax.random.PRNGKey(0), jnp.zeros((1, config["seq_len"]), dtype=jnp.int32)
    )["params"]
    params = from_bytes(template, (path / "params.msgpack").read_bytes())
    return model, params, vocab
