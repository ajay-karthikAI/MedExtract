"""Fine-tune a token-classification model on synthetic MedExtract data.

Trains a small transformer to tag conditions/symptoms/medications/procedures
(BIO scheme) and saves a checkpoint that inference.py picks up automatically:

    python -m pytorch_pipeline.train --epochs 3 --train-size 300

The synthetic dataset is trivially easy by design — this is pipeline plumbing
you can later point at a real, licensed, de-identified corpus.
"""

import argparse
from pathlib import Path

from .model import BIO_LABELS, CHECKPOINT_DIR
from .synthetic import generate_dataset


def build_examples(samples, tokenizer, max_length: int):
    """Tokenize notes and align char-level gold spans to BIO token labels."""
    label_to_id = {label: i for i, label in enumerate(BIO_LABELS)}
    examples = []
    for text, spans in samples:
        enc = tokenizer(
            text,
            truncation=True,
            max_length=max_length,
            return_offsets_mapping=True,
        )
        labels = []
        previous_span = None
        for start, end in enc["offset_mapping"]:
            if start == end:  # special token
                labels.append(-100)
                continue
            token_label = "O"
            for span_start, span_end, category in spans:
                if start >= span_start and end <= span_end:
                    prefix = "B" if previous_span != (span_start, span_end) else "I"
                    token_label = f"{prefix}-{category}"
                    previous_span = (span_start, span_end)
                    break
            else:
                previous_span = None
            labels.append(label_to_id[token_label])
        enc["labels"] = labels
        enc.pop("offset_mapping")
        examples.append(enc)
    return examples


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-model", default="distilbert-base-uncased")
    parser.add_argument("--train-size", type=int, default=300)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=5e-5)
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--output", type=Path, default=CHECKPOINT_DIR)
    args = parser.parse_args()

    import torch
    from torch.utils.data import DataLoader
    from transformers import (
        AutoModelForTokenClassification,
        AutoTokenizer,
        DataCollatorForTokenClassification,
        set_seed,
    )

    set_seed(args.seed)
    tokenizer = AutoTokenizer.from_pretrained(args.base_model)
    model = AutoModelForTokenClassification.from_pretrained(
        args.base_model,
        num_labels=len(BIO_LABELS),
        id2label=dict(enumerate(BIO_LABELS)),
        label2id={label: i for i, label in enumerate(BIO_LABELS)},
    )

    samples = generate_dataset(args.train_size, seed=args.seed)
    examples = build_examples(samples, tokenizer, args.max_length)
    collator = DataCollatorForTokenClassification(tokenizer)
    loader = DataLoader(examples, batch_size=args.batch_size, shuffle=True, collate_fn=collator)

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)
    model.train()
    for epoch in range(args.epochs):
        total_loss = 0.0
        for batch in loader:
            optimizer.zero_grad()
            loss = model(**batch).loss
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        print(f"epoch {epoch + 1}/{args.epochs} — mean loss {total_loss / len(loader):.4f}")

    args.output.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.output)
    tokenizer.save_pretrained(args.output)
    print(f"saved checkpoint to {args.output}")
    print("inference.py will now prefer this checkpoint over the pretrained default.")


if __name__ == "__main__":
    main()
