"""Run the rule-based Scanner diagnostic on permitted local inputs."""
from __future__ import annotations

import argparse
import csv
import shutil
from collections import defaultdict
from pathlib import Path
from random import Random
from tempfile import TemporaryDirectory

from data_pipeline.core import Run
from data_pipeline.sources.contracts import FX_PATTERN, prepare

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/scanner"


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def audit_cuad(archive):
    with TemporaryDirectory(prefix="cuad-", dir=OUT) as directory:
        work = Path(directory)
        shutil.copytree(ROOT / "configs", work / "configs")
        run = Run(work)
        try:
            run.import_raw("cuad", "archive", run.sources["cuad"]["endpoint"], archive)
            docs, candidates, _, _, _, _, _, reviewed = prepare(run)
        finally:
            run.close()
    hit_docs = {row["document_id"] for row in candidates}
    by_id = {row["document_id"]: row for row in docs}
    for row in candidates:
        doc = by_id[row["document_id"]]
        assert row["text_hash"] == doc["text_hash"]
        assert doc["text"][row["start"]:row["end"]] == row["matched_text"]
    audited = []
    for r in reviewed:
        doc = by_id[r["document_id"]]
        assert r["category"] in {"confirmed_fx", "confirmed_negative"}
        predicted = bool(FX_PATTERN.search(doc["text"]))
        audited.append({"sample": "reviewed_en", "example": len(audited) + 1,
                        "expected": r["category"] == "confirmed_fx", "candidate_found": predicted})
    anchor_ids = {r["document_id"] for r in reviewed}
    grouped = defaultdict(list)
    for doc in docs:
        grouped[doc.get("dedup_group") or doc["text_hash"]].append(doc)
    anchor_groups = {key for key, members in grouped.items() if any(d["document_id"] in anchor_ids for d in members)}
    strata = defaultdict(list)
    for key, members in sorted(grouped.items()):
        if key in anchor_groups:
            continue
        strata[any(m["document_id"] in hit_docs for m in members)].append(key)
    rng = Random(20261114)
    queue = []
    for hits in (True, False):
        choices = strata[hits]
        rng.shuffle(choices)
        if len(choices) < 30:
            raise ValueError("Insufficient document groups for the review queue")
        for i, key in enumerate(choices[:30]):
            for d in sorted(grouped[key], key=lambda item: item["document_id"]):
                queue.append({"split": "development" if i < 10 else "holdout", "sampling_stratum": "rule_hit" if hits else "no_rule_hit",
                              "document_id": d["document_id"], "dedup_group": key, "text_hash": d["text_hash"],
                              "reviewer_status": "unreviewed"})
    write_csv(OUT / "scanner_review_queue.csv", queue)
    return {"docs": len(docs), "hits": len(candidates), "reviewed": audited, "queue_documents": len(queue)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cuad", type=Path, help="Original, separately downloaded CUAD_v1.zip")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    with (ROOT / "configs/court_examples.csv").open(encoding="utf-8-sig", newline="") as stream:
        diagnostics = [
            {"sample": "court_excerpt_ru_positive_only", "example": row["reference_currency"],
             "expected": True, "candidate_found": bool(FX_PATTERN.search(row["evidence"]))}
            for row in csv.DictReader(stream)
        ]
    print(f"Scanner RU: {sum(d['candidate_found'] for d in diagnostics)}/{len(diagnostics)} diagnostic positives detected.")
    write_csv(OUT / "scanner_ru_checks.csv", diagnostics)
    if args.cuad:
        result = audit_cuad(args.cuad.resolve(strict=True))
        write_csv(OUT / "scanner_en_checks.csv", result["reviewed"])
        print(f'Scanner EN: {result["docs"]} documents, {result["hits"]} candidates, '
              f'{result["queue_documents"]} queued reviews.')
    else:
        print("CUAD is optional. Pass --cuad PATH to run the English corpus and review-queue experiments.")


if __name__ == "__main__":
    main()
