"""PyTorch clinical NER training skeleton.

Token-classification (BIO) over labels: condition, symptom, medication, procedure.
Fill in dataset loading and swap the base model as needed. Synthetic /
de-identified data only.
"""

import argparse

LABELS = [
    "O",
    "B-CONDITION", "I-CONDITION",
    "B-SYMPTOM", "I-SYMPTOM",
    "B-MEDICATION", "I-MEDICATION",
    "B-PROCEDURE", "I-PROCEDURE",
]


def build_model(base_model: str):
    from transformers import AutoModelForTokenClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(base_model)
    model = AutoModelForTokenClassification.from_pretrained(
        base_model,
        num_labels=len(LABELS),
        id2label=dict(enumerate(LABELS)),
        label2id={l: i for i, l in enumerate(LABELS)},
    )
    return tokenizer, model


def load_dataset(path: str):
    """TODO: load BIO-tagged training data (e.g. CoNLL format) from `path`."""
    raise NotImplementedError("Provide a synthetic/de-identified NER dataset")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, help="Path to BIO-tagged dataset")
    parser.add_argument("--base-model", default="distilbert-base-uncased")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--output", default="checkpoints/")
    args = parser.parse_args()

    tokenizer, model = build_model(args.base_model)
    dataset = load_dataset(args.data)
    # TODO: tokenize + align labels, then train with transformers.Trainer
    raise NotImplementedError("Training loop not implemented yet")


if __name__ == "__main__":
    main()
