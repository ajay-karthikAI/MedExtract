"""Evaluate the active PyTorch pipeline on held-out synthetic notes.

Runs `inference.extract` (fine-tuned checkpoint if present, else the pretrained
biomedical model) against gold spans and reports span-level precision, recall,
and F1 per category:

    python -m pytorch_pipeline.evaluate --size 50
"""

import argparse
from collections import defaultdict

from . import inference
from .model import CATEGORIES
from .synthetic import generate_dataset


def spans_overlap(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def evaluate(size: int, seed: int) -> dict[str, dict[str, float]]:
    # Different seed space from train.py's default so this stays held-out.
    samples = generate_dataset(size, seed=seed)
    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})

    for text, gold in samples:
        result = inference.extract(text)
        predicted = [
            (e["span_start"], e["span_end"], e["category"])
            for key in ("conditions", "symptoms", "medications", "procedures")
            for e in result[key]
        ]
        matched_gold: set[int] = set()
        for p_start, p_end, p_cat in predicted:
            hit = next(
                (
                    i
                    for i, (g_start, g_end, g_cat) in enumerate(gold)
                    if i not in matched_gold
                    and g_cat == p_cat
                    and spans_overlap((p_start, p_end), (g_start, g_end))
                ),
                None,
            )
            if hit is None:
                counts[p_cat]["fp"] += 1
            else:
                matched_gold.add(hit)
                counts[p_cat]["tp"] += 1
        for i, (_, _, g_cat) in enumerate(gold):
            if i not in matched_gold:
                counts[g_cat]["fn"] += 1

    metrics: dict[str, dict[str, float]] = {}
    total = {"tp": 0, "fp": 0, "fn": 0}
    for category in CATEGORIES:
        c = counts[category]
        for k in total:
            total[k] += c[k]
        metrics[category] = _prf(c)
    metrics["micro"] = _prf(total)
    return metrics


def _prf(c: dict[str, int]) -> dict[str, float]:
    precision = c["tp"] / (c["tp"] + c["fp"]) if c["tp"] + c["fp"] else 0.0
    recall = c["tp"] / (c["tp"] + c["fn"]) if c["tp"] + c["fn"] else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=int, default=50)
    parser.add_argument("--seed", type=int, default=99)
    args = parser.parse_args()

    print(f"model: {inference.model_name()}")
    metrics = evaluate(args.size, args.seed)
    print(f"{'category':<12} {'precision':>9} {'recall':>7} {'f1':>6}")
    for category, m in metrics.items():
        print(f"{category:<12} {m['precision']:>9.3f} {m['recall']:>7.3f} {m['f1']:>6.3f}")


if __name__ == "__main__":
    main()
