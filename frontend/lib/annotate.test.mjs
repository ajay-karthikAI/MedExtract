import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import ts from "typescript";

async function loadAnnotateModule() {
  const source = await readFile(new URL("./annotate.ts", import.meta.url), "utf8");
  const transpiled = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2022,
    },
  }).outputText;
  const url = `data:text/javascript;base64,${Buffer.from(transpiled).toString("base64")}`;
  return import(url);
}

const annotate = await loadAnnotateModule();

test("uses explicit spans when present", () => {
  const note = "PMH: HTN.";
  const annotations = annotate.buildEntityAnnotations(note, [
    {
      id: "condition:htn",
      entity: {
        category: "condition",
        text: "HTN",
        normalized: "hypertension",
        span_start: 5,
        span_end: 8,
        confidence: 0.85,
        source: "rule",
        warning: null,
      },
    },
  ]);

  assert.deepEqual(annotations.map(({ start, end }) => [start, end]), [[5, 8]]);
});

test("falls back to case-insensitive matching", () => {
  const note = "Reports SOB. SOB improved.";
  const annotations = annotate.buildEntityAnnotations(note, [
    {
      id: "symptom:sob",
      entity: {
        category: "symptom",
        text: "sob",
        normalized: "shortness of breath",
        span_start: null,
        span_end: null,
        confidence: 0.82,
        source: "rule",
        warning: null,
      },
    },
  ]);

  assert.deepEqual(annotations.map(({ start, end }) => [start, end]), [[8, 11], [13, 16]]);
});

test("prefers longer overlapping spans", () => {
  const note = "type 2 diabetes mellitus";
  const annotations = annotate.buildEntityAnnotations(note, [
    {
      id: "condition:diabetes",
      entity: {
        category: "condition",
        text: "diabetes",
        normalized: "diabetes mellitus",
        span_start: null,
        span_end: null,
        confidence: 0.7,
        source: "model",
        warning: null,
      },
    },
    {
      id: "condition:t2dm",
      entity: {
        category: "condition",
        text: "type 2 diabetes mellitus",
        normalized: "type 2 diabetes mellitus",
        span_start: null,
        span_end: null,
        confidence: 0.86,
        source: "rule",
        warning: null,
      },
    },
  ]);

  assert.equal(annotations.length, 1);
  assert.equal(annotations[0].id, "condition:t2dm");
});
