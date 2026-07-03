"""Train the Flax note-category classifier on synthetic specialty-labeled notes.

    python -m jax_pipeline.train --train-size 480 --epochs 20

Uses the same synthetic generator as the TensorFlow pipeline (same default
seed and size) so the two classifiers train on identical data — this pipeline
exists for research comparison. Saves params (msgpack) + vocab (json) to a
checkpoint dir that inference.py picks up automatically.
"""

import argparse
from pathlib import Path

from tensorflow_pipeline.synthetic import CATEGORIES, generate_dataset

from .model import CHECKPOINT_DIR, build_classifier, build_vocab, save_checkpoint, tokenize


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-size", type=int, default=480)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--output", type=Path, default=CHECKPOINT_DIR)
    args = parser.parse_args()

    import jax
    import jax.numpy as jnp
    import numpy as np
    import optax
    from flax.training.train_state import TrainState

    samples = generate_dataset(args.train_size, seed=args.seed)
    texts = [text for text, _, _ in samples]
    vocab = build_vocab(texts)
    ids = np.array([tokenize(t, vocab) for t in texts], dtype=np.int32)
    labels = np.array([CATEGORIES.index(spec) for _, _, spec in samples], dtype=np.int32)

    # 90/10 train/validation split
    rng = np.random.default_rng(args.seed)
    order = rng.permutation(len(ids))
    split = int(len(ids) * 0.9)
    train_idx, val_idx = order[:split], order[split:]

    model = build_classifier(vocab_size=len(vocab) + 2)
    params = model.init(jax.random.PRNGKey(args.seed), jnp.asarray(ids[:1]))["params"]
    state = TrainState.create(apply_fn=model.apply, params=params, tx=optax.adam(args.lr))

    @jax.jit
    def train_step(state, xb, yb):
        def loss_fn(p):
            logits = state.apply_fn({"params": p}, xb)
            return optax.softmax_cross_entropy_with_integer_labels(logits, yb).mean(), logits

        (loss, logits), grads = jax.value_and_grad(loss_fn, has_aux=True)(state.params)
        return state.apply_gradients(grads=grads), loss, (logits.argmax(-1) == yb).mean()

    @jax.jit
    def accuracy(state, xb, yb):
        return (state.apply_fn({"params": state.params}, xb).argmax(-1) == yb).mean()

    for epoch in range(args.epochs):
        rng.shuffle(train_idx)
        losses, accs = [], []
        for i in range(0, len(train_idx), args.batch_size):
            batch = train_idx[i : i + args.batch_size]
            state, loss, acc = train_step(state, jnp.asarray(ids[batch]), jnp.asarray(labels[batch]))
            losses.append(float(loss))
            accs.append(float(acc))
        if (epoch + 1) % 5 == 0 or epoch == args.epochs - 1:
            val_acc = float(accuracy(state, jnp.asarray(ids[val_idx]), jnp.asarray(labels[val_idx])))
            print(
                f"epoch {epoch + 1}/{args.epochs} — loss {sum(losses) / len(losses):.4f} "
                f"· train acc {sum(accs) / len(accs):.3f} · val acc {val_acc:.3f}"
            )

    save_checkpoint(state.params, vocab, args.output)
    print(f"saved checkpoint to {args.output}")
    print("inference.py will now use the trained classifier for confidence boosting.")


if __name__ == "__main__":
    main()
