"""Evaluate the JAX/Flax research pipeline on held-out synthetic notes.

Reports note-category accuracy, span-level entity precision/recall/F1, and
mean per-note inference latency (this pipeline exists for benchmarking).
Uses the same held-out seed as tensorflow_pipeline.evaluate so results are
directly comparable:

    python -m jax_pipeline.evaluate --size 80
"""

import argparse
import time
from collections import defaultdict

from tensorflow_pipeline.synthetic import generate_dataset

from . import inference

ENTITY_CATEGORIES = ("condition", "symptom", "medication", "procedure")
GROUP_KEYS = ("conditions", "symptoms", "medications", "procedures")


def spans_overlap(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def _prf(c: dict[str, int]) -> dict[str, float]:
    precision = c["tp"] / (c["tp"] + c["fp"]) if c["tp"] + c["fp"] else 0.0
    recall = c["tp"] / (c["tp"] + c["fn"]) if c["tp"] + c["fn"] else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=int, default=80)
    parser.add_argument("--seed", type=int, default=101)  # same held-out seed as TF evaluate
    args = parser.parse_args()

    samples = generate_dataset(args.size, seed=args.seed)
    print(f"model: {inference.model_name()}")

    inference.extract(samples[0][0])  # warm-up: JIT compile outside the timed loop

    correct_category = 0
    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    started = time.perf_counter()

    for text, gold, specialty in samples:
        predicted_specialty, _ = inference.classify(text)
        if predicted_specialty == specialty:
            correct_category += 1

        result = inference.extract(text)
        predicted = [
            (e["span_start"], e["span_end"], e["category"])
            for key in GROUP_KEYS
            for e in result[key]
        ]
        matched: set[int] = set()
        for p_start, p_end, p_cat in predicted:
            hit = next(
                (
                    i
                    for i, (g_start, g_end, g_cat) in enumerate(gold)
                    if i not in matched
                    and g_cat == p_cat
                    and spans_overlap((p_start, p_end), (g_start, g_end))
                ),
                None,
            )
            if hit is None:
                counts[p_cat]["fp"] += 1
            else:
                matched.add(hit)
                counts[p_cat]["tp"] += 1
        for i, (_, _, g_cat) in enumerate(gold):
            if i not in matched:
                counts[g_cat]["fn"] += 1

    elapsed = time.perf_counter() - started
    print(f"note-category accuracy: {correct_category / len(samples):.3f} ({len(samples)} notes)")
    print(f"{'category':<12} {'precision':>9} {'recall':>7} {'f1':>6}")
    total = {"tp": 0, "fp": 0, "fn": 0}
    for category in ENTITY_CATEGORIES:
        c = counts[category]
        for k in total:
            total[k] += c[k]
        m = _prf(c)
        print(f"{category:<12} {m['precision']:>9.3f} {m['recall']:>7.3f} {m['f1']:>6.3f}")
    m = _prf(total)
    print(f"{'micro':<12} {m['precision']:>9.3f} {m['recall']:>7.3f} {m['f1']:>6.3f}")
    print(
        f"latency: {elapsed / len(samples) * 1000:.1f} ms/note "
        f"({len(samples) / elapsed:.0f} notes/s, classify+extract, CPU)"
    )


if __name__ == "__main__":
    main()
