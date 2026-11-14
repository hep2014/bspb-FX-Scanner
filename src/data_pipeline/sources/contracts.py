from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
from xml.etree import ElementTree
from zipfile import ZipFile

from lxml import html

from data_pipeline.core import Run, Raw, SourceError

FX_PATTERN = re.compile(
    r"\b(?:currency adjustment|exchange rates?|foreign currency|payment currency|"
    r"currency conversion|purchase price adjustment|exchange rate fluctuation|"
    r"валютн\w+\s+оговорк\w+|курс(?:а|у|ом)?\s+(?:обмен\w+|валют\w+|доллар\w+|евро|юан\w+|ЦБ)|"
    r"курсов\w+\s+разниц\w+|(?:пересчет|пересчёт)\w*\s+(?:цен\w+|обязательств\w+)|"
    r"USD|EUR|CNY)\b|(?<!\w)US\$(?=\s*\d)", re.I,
)
CUAD_RELATED = re.compile(
    r"effective date|expiration date|renewal term|notice period|minimum commitment|"
    r"revenue/profit sharing|price|payment|liquidated damages|volume restriction|audit rights|"
    r"most favored nation|uncapped liability|cap on liability", re.I,
)
EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
IBAN = re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]){10,30}\b")
ACCOUNT = re.compile(r"(?<!\d)\d{20}(?!\d)")
PHONE = re.compile(r"(?<!\w)(?:\+?\d{1,3}[ .-])?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\w)")
APPROVED_LICENSES = {"cc-by-4.0", "public-domain", "research-use-approved", "permission-confirmed"}
VALID_LABELS = {"confirmed_fx", "confirmed_negative", ""}
LABELS_NLI = {
    "Entailment": "entailment",
    "Contradiction": "contradiction",
    "NotMentioned": "not_mentioned",
}


def manifest_rows(run: Run):
    with (run.root / "configs/contract_documents.csv").open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            if row["source_id"] not in {"eis", "sec", "stanford_mcc"}:
                raise SourceError(f"Unknown contract manifest source {row['source_id']}")
            if row["license_status"].lower() not in APPROVED_LICENSES:
                raise SourceError(f"Reuse permission missing for {row['document_id']}")
            if row["pii_status"] not in {"reviewed_no_pii", "redacted"}:
                raise SourceError(f"PII review required for {row['document_id']}")
            if row["reviewed_label"] not in VALID_LABELS:
                raise SourceError(f"Unknown review label for {row['document_id']}")
            yield row


def download_cuad(run: Run) -> None:
    source = run.sources["cuad"]
    run.fetch("cuad", "archive", source["endpoint"], ".zip", source["md5"])
    run.fetch("cuad", "categories", source["categories_endpoint"], ".csv")


def collect_external(run: Run, source_id: str) -> str:
    selected = [row for row in manifest_rows(run) if row["source_id"] == source_id]
    if not selected:
        return run.sources[source_id]["manual"]
    for row in selected:
        key = row["document_id"]
        url = row["url"]
        if row["local_path"]:
            run.import_raw(source_id, key, url, run.path(row["local_path"]))
        else:
            suffix = Path(urlsplit(url).path).suffix.lower()
            run.fetch(source_id, key, url, suffix if suffix in {".pdf", ".txt", ".docx"} else ".html")
    return ""


def archive_member(archive: ZipFile, filename: str) -> str:
    matches = [item.filename for item in archive.infolist()
               if not item.is_dir() and PurePosixPath(item.filename).name.casefold() == filename.casefold()]
    if len(matches) != 1:
        raise SourceError(f"Expected exactly one {filename}, got {len(matches)}")
    return matches[0]


def archive_json(archive: ZipFile, filename: str):
    name = archive_member(archive, filename)
    if archive.getinfo(name).file_size > 100 * 1024**2:
        raise SourceError(f"Unexpected unpacked JSON size for {filename}")
    return json.loads(archive.read(name))


def language(text: str) -> str:
    sample = text[:10000]
    latin = len(re.findall(r"[a-zA-Z]", sample))
    cyrillic = len(re.findall(r"[а-яА-ЯёЁ]", sample))
    if latin + cyrillic == 0:
        return "und"
    return "ru" if cyrillic > latin else "en"


def mask_pii(text: str) -> tuple[str, bool]:
    original = text
    for pattern in (EMAIL, IBAN, ACCOUNT, PHONE):
        text = pattern.sub(lambda match: "█" * len(match[0]), text)
    return text, text != original


def document(raw: Raw, document_id: str, text: str, document_type: str, source_url: str,
             publication_date: str | None, file_format: str, extraction_method: str,
             license_status: str, pii_status: str, declared_language: str | None = None):
    redacted, changed = mask_pii(text)
    if changed:
        pii_status = "pattern_redaction_applied_manual_review_pending"
    return {
        "document_id": document_id, "source_dataset": raw.source_id, "source_id": raw.source_id,
        "source_document_id": document_id,
        "source_url": source_url, "document_type": document_type,
        "language": declared_language or language(redacted), "publication_date": publication_date,
        "text": redacted, "text_hash": hashlib.sha256(redacted.encode()).hexdigest(),
        "file_format": file_format, "currency_clause_candidate": False,
        "license_status": license_status, "pii_status": pii_status,
        "extraction_method": extraction_method, "source_sha256": raw.sha256,
    }


def cuad_documents(raw: Raw):
    with ZipFile(raw.path) as archive:
        payload = archive_json(archive, "CUAD_v1.json")
    for entry in payload["data"]:
        paragraphs = entry["paragraphs"]
        title = str(entry["title"])
        key = hashlib.sha256(title.encode()).hexdigest()[:20]
        text = "\n\n".join(p["context"] for p in paragraphs)
        row = document(raw, f"cuad_{key}", text, "commercial_contract", raw.url, None, "json",
                       "CUAD SQuAD context", "cc-by-4.0",
                       "automated_pii_scan_only", "en")
        row["source_document_id"] = title
        offset = 0
        labels = []
        for paragraph in paragraphs:
            for qa in paragraph.get("qas", []):
                qid = str(qa.get("id", ""))
                category = qid.rsplit("__", 1)[-1] if "__" in qid else qa.get("question", "")
                for answer in qa.get("answers", []):
                    start = offset + int(answer["answer_start"])
                    end = start + len(answer["text"])
                    labels.append({"document_id": row["document_id"], "label_source": "CUAD",
                                   "qa_id": qid, "category": category,
                                   "fx_relevance_candidate": bool(CUAD_RELATED.search(category)),
                                   "start": start, "end": end,
                                   "evidence": row["text"][start:end],
                                   "original_span_aligned": text[start:end] == answer["text"],
                                   "source_id": raw.source_id, "source_sha256": raw.sha256})
            offset += len(paragraph["context"]) + 2
        yield row, labels


def nli_records(raw: Raw):
    with ZipFile(raw.path) as archive:
        for split in ("train", "dev", "test"):
            payload = archive_json(archive, f"{split}.json")
            for doc in payload["documents"]:
                text, _ = mask_pii(doc["text"])
                for annotation in doc.get("annotation_sets", []):
                    for hypothesis, value in annotation["annotations"].items():
                        original = value["choice"]
                        if original not in LABELS_NLI:
                            raise SourceError(f"Unknown ContractNLI label: {original}")
                        evidence_indices = value.get("spans", [])
                        yield {
                            "document_id": f"contractnli_{doc['id']}", "original_split": split,
                            "hypothesis_id": hypothesis, "label": LABELS_NLI[original],
                            "hypothesis": payload["labels"][hypothesis]["hypothesis"],
                            "label_original": original, "evidence_span_indices": evidence_indices,
                            "evidence_spans": [doc["spans"][i] for i in evidence_indices],
                            "evidence_text": [text[s:e] for s, e in (doc["spans"][i] for i in evidence_indices)],
                            "source_url": doc.get("url"), "source_id": raw.source_id, "source_sha256": raw.sha256,
                        }


def reviewed_cuad(run: Run):
    with (run.root / "configs/cuad_review.csv").open(encoding="utf-8-sig", newline="") as stream:
        return {row["document_id"]: row for row in csv.DictReader(stream)}


def review_label(row: dict, annotation: dict) -> dict:
    if annotation["text_hash"] != row["text_hash"]:
        raise SourceError(f"Reviewed document changed: {row['document_id']}")
    result = annotation["reviewed_label"]
    if result not in {"confirmed_fx", "confirmed_negative"}:
        raise SourceError(f"Invalid reviewed label for {row['document_id']}")
    start, end = int(annotation["start"]), int(annotation["end"])
    if not 0 <= start < end <= len(row["text"]):
        raise SourceError(f"Invalid reviewed span for {row['document_id']}")
    return {
        "document_id": row["document_id"], "label_source": "assistant_review",
        "category": result, "start": start, "end": end,
        "evidence": row["text"][start:end], "review_note": annotation["review_note"],
        "source_id": row["source_id"], "source_sha256": row["source_sha256"],
    }


def text_from_file(raw: Raw) -> str:
    suffix = raw.path.suffix
    if suffix == ".txt":
        return raw.path.read_text(encoding="utf-8-sig")
    if suffix == ".html":
        tree = html.parse(raw.path)
        for node in tree.xpath("//script|//style|//nav|//header|//footer"):
            node.drop_tree()
        return "\n".join(s.strip() for s in tree.getroot().itertext() if s.strip())
    if suffix == ".docx":
        with ZipFile(raw.path) as archive:
            root = ElementTree.fromstring(archive.read("word/document.xml"))
        namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        return "\n".join("".join(t.text or "" for t in p.iter(namespace + "t"))
                         for p in root.iter(namespace + "p"))
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise SourceError("PDF extraction requires the optional pdf dependencies") from exc
        return "\n".join(page.extract_text() or "" for page in PdfReader(raw.path).pages)
    raise SourceError(f"Unrecognized document format: {suffix}")


def court_examples(run: Run):
    with (run.root / "configs/court_examples.csv").open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            for raw in run.raw("russian_court", row["document_id"]):
                page = html.parse(raw.path)
                body = " ".join(page.xpath("string(//body)").split())
                evidence = row["evidence"]
                if evidence.casefold() not in body.casefold():
                    raise SourceError(f"Court evidence cannot be verified: {row['document_id']}")
                yield {
                    **row, "source_id": raw.source_id, "source_url": raw.url, "source_sha256": raw.sha256,
                    "document_type": "court_decision_excerpt", "language": "ru", "payment_currency": "RUB",
                    "label_origin": "assistant_review", "pii_status": "reviewed_no_pii_in_excerpt",
                }


def candidate_spans(row: dict, context: int):
    text = row["text"]
    for match in FX_PATTERN.finditer(text):
        start, end = match.span()
        yield {
            "candidate_id": f"{row['document_id']}:{start}:{end}",
            "document_id": row["document_id"], "source_id": row["source_id"],
            "source_url": row["source_url"], "source_sha256": row["source_sha256"],
            "text_hash": row["text_hash"], "start": start, "end": end, "matched_text": match[0],
            "context_start": max(0, start - context),
            "context": text[max(0, start - context):end + context],
            "label_origin": "keyword_rule", "reviewer_status": "unreviewed",
        }


def annotation_template(row: dict | None, candidate: dict | None = None) -> dict:
    value = {
        "document_id": row["document_id"] if row else None,
        "text_hash": row["text_hash"] if row else None,
        "candidate_id": candidate["candidate_id"] if candidate else None,
        "exposure_exists": None, "clause_type": None, "reference_currency": None,
        "payment_currency": None, "notional_amount": None, "fixing_date": None,
        "payment_date": None, "exchange_rate_source": None, "conversion_formula": None,
        "exposure_direction": None, "evidence_span": None,
        "annotation_confidence": None, "reviewer_status": "unreviewed",
    }
    if candidate:
        value["proposed_span"] = [candidate["start"], candidate["end"]]
    return value


def prepare(run: Run):
    docs = []
    labels = []
    nli = []
    for raw in run.raw("cuad", "archive"):
        docs.extend(cuad_documents(raw))
    for raw in run.raw("contractnli", "archive"):
        nli.extend(nli_records(raw))
    human = {}
    reviewed = reviewed_cuad(run)
    for item in manifest_rows(run):
        for raw in run.raw(item["source_id"], item["document_id"], item["url"]):
            row = document(raw, item["document_id"], text_from_file(raw), item["document_type"],
                           item["url"], item["publication_date"] or None, raw.path.suffix[1:],
                           "plain text extraction", item["license_status"], item["pii_status"],
                           item["language"] or None)
            docs.append((row, []))
            if item["reviewed_label"]:
                human[row["document_id"]] = item["reviewed_label"]
                if item["reviewed_label"] == "confirmed_fx":
                    try:
                        start, end = int(item["evidence_start"]), int(item["evidence_end"])
                    except ValueError as exc:
                        raise SourceError(f"Confirmed document lacks a checked span: {row['document_id']}") from exc
                    if not 0 <= start < end <= len(row["text"]):
                        raise SourceError(f"Invalid reviewed span: {row['document_id']}")
                    labels.append({
                        "document_id": row["document_id"], "label_source": "human_fx",
                        "category": "confirmed_fx", "start": start, "end": end,
                        "evidence": row["text"][start:end], "source_id": raw.source_id,
                        "source_sha256": raw.sha256,
                    })
    corpus, candidates, tasks, reviewed_labels = [], [], [], []
    groups = defaultdict(list)
    dropped = []
    seen_ids = set()
    for row, annotations in docs:
        if row["document_id"] in seen_ids:
            raise SourceError(f"Duplicate document identifier: {row['document_id']}")
        seen_ids.add(row["document_id"])
        text = row["text"]
        if len(text.strip()) < run.settings["contract_min_characters"] or "\ufffd" in text:
            dropped.append(row["document_id"])
            continue
        normalized = " ".join(text.casefold().split())
        fingerprint = hashlib.sha256(normalized.encode()).hexdigest()
        groups[fingerprint].append(row["document_id"])
        if len(groups[fingerprint]) > 1:
            continue
        row["dedup_group"] = fingerprint
        matches = list(candidate_spans(row, run.settings["candidate_context_chars"]))
        row["currency_clause_candidate"] = bool(matches)
        review = reviewed.get(row["document_id"])
        if review:
            reviewed_labels.append(review_label(row, review))
            human[row["document_id"]] = review["reviewed_label"]
        row["corpus_class"] = human.get(row["document_id"]) or (
            "weak_fx_candidate" if matches else "unreviewed_no_hit"
        )
        corpus.append(row)
        candidates.extend(matches)
        labels.extend(annotations)
        tasks.extend(annotation_template(row, hit) for hit in matches)
        if not matches:
            tasks.append(annotation_template(row))
    kept = {row["document_id"] for row in corpus}
    labels = [row for row in labels if row["document_id"] in kept]
    duplicates = [{"dedup_group": key, "documents": ids} for key, ids in groups.items() if len(ids) > 1]
    return corpus, candidates, tasks, labels, nli, duplicates, dropped, reviewed_labels
