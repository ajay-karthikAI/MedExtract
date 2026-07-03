"""Train the Keras note-category classifier on synthetic specialty-labeled notes.

    python -m tensorflow_pipeline.train --train-size 480 --epochs 12

Saves a self-contained .keras model (tokenizer included) that inference.py
picks up automatically. Synthetic data is trivially easy by design — this is
pipeline plumbing to later point at a real, licensed, de-identified corpus.
"""

import argparse
from pathlib import Path

from .model import CHECKPOINT, build_model
from .synthetic import CATEGORIES, generate_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-size", type=int, default=480)
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--output", type=Path, default=CHECKPOINT)
    args = parser.parse_args()

    import numpy as np
    import tensorflow as tf

    tf.keras.utils.set_random_seed(args.seed)

    samples = generate_dataset(args.train_size, seed=args.seed)
    # tf.string tensors, not numpy str arrays — Keras 3 rejects fixed-width numpy strings
    texts = tf.constant([[text] for text, _, _ in samples])
    labels = np.array([CATEGORIES.index(spec) for _, _, spec in samples])

    model, vectorize = build_model()
    vectorize.adapt(tf.constant([text for text, _, _ in samples]))
    model.compile(
        optimizer="adam",
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    history = model.fit(
        texts,
        labels,
        epochs=args.epochs,
        batch_size=args.batch_size,
        validation_split=0.1,
        verbose=2,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    model.save(args.output)
    final = history.history
    print(
        f"final train acc {final['accuracy'][-1]:.3f} · "
        f"val acc {final['val_accuracy'][-1]:.3f}"
    )
    print(f"saved checkpoint to {args.output}")
    print("inference.py will now use the trained classifier for confidence boosting.")


if __name__ == "__main__":
    main()
