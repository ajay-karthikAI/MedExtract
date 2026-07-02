"""TensorFlow clinical NER training skeleton.

Same task and label scheme as ml/pytorch: BIO token classification over
condition / symptom / medication / procedure. Synthetic / de-identified data only.
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
    from transformers import AutoTokenizer, TFAutoModelForTokenClassification

    tokenizer = AutoTokenizer.from_pretrained(base_model)
    model = TFAutoModelForTokenClassification.from_pretrained(
        base_model,
        num_labels=len(LABELS),
        id2label=dict(enumerate(LABELS)),
        label2id={l: i for i, l in enumerate(LABELS)},
    )
    return tokenizer, model


def load_dataset(path: str):
    """TODO: load BIO-tagged training data and convert to tf.data.Dataset."""
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
    # TODO: model.compile(...) + model.fit(...)
    raise NotImplementedError("Training loop not implemented yet")


if __name__ == "__main__":
    main()
