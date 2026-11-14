from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import httpx
import yaml
from pydantic import BaseModel, Field

LOG = logging.getLogger(__name__)

STATUS_OK = "VERIFIED_AND_DOWNLOADED"
STATUS_WARN = "DOWNLOADED_WITH_WARNINGS"
STATUS_RESTRICTED = "ACCESS_RESTRICTED"
STATUS_ABSENT = "NOT_AVAILABLE"
STATUS_UNVERIFIED = "NOT_VERIFIED"


class SourceError(RuntimeError):
    def __init__(self, message: str, status: str = STATUS_UNVERIFIED):
        super().__init__(message)
        self.status = status


class Settings(BaseModel):
    start_date: date
    end_date: date
    timeout_seconds: float = Field(gt=0)
    attempts: int = Field(ge=1, le=6)
    minimum_request_interval: float = Field(ge=0)
    max_response_mib: int = Field(ge=1)
    spot_jump_threshold: float = Field(gt=0)
    contract_min_characters: int = Field(ge=1)
    candidate_context_chars: int = Field(ge=0)
    moex: dict


def now() -> str:
    return datetime.now(ZoneInfo("Europe/Moscow")).isoformat(timespec="seconds")


def digest(path: Path, algorithm: str = "sha256") -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, delete=False, suffix=".part") as temporary:
        staged = Path(temporary.name)
        try:
            temporary.write(data)
            temporary.close()
            os.replace(staged, path)
        finally:
            staged.unlink(missing_ok=True)


def write_json(path: Path, value) -> None:
    atomic_write(path, (json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n").encode())


def read_json(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def check_format(path: Path, suffix: str) -> None:
    with path.open("rb") as stream:
        prefix = stream.read(2048).lstrip(b"\xef\xbb\xbf \r\n\t")
    expected = {
        ".pdf": (b"%PDF-",),
        ".zip": (b"PK",),
        ".xlsx": (b"PK",),
        ".xls": (bytes.fromhex("D0CF11E0A1B11AE1"), b"PK"),
        ".docx": (b"PK",),
        ".7z": (b"7z\xbc\xaf\x27\x1c",),
        ".json": (b"{", b"["),
        ".xml": (b"<?xml", b"<ValCurs", b"<Valuta"),
        ".html": (b"<",),
    }
    if not prefix or (suffix in expected and not prefix.startswith(expected[suffix])):
        raise SourceError(f"Unexpected or empty payload for {suffix}: {path.name}")
    if suffix == ".html" and any(marker in prefix.lower() for marker in (
        b"just a moment...", b"captcha challenge", b"request rate threshold exceeded",
        b"undeclared automated tool",
    )):
        raise SourceError("HTML access challenge", STATUS_RESTRICTED)


@dataclass(frozen=True)
class Raw:
    key: str
    source_id: str
    url: str
    path: Path
    sha256: str
    size: int
    fetched_at: str
    method: str

    def reference(self) -> dict:
        return {"source_id": self.source_id, "source": self.url, "source_sha256": self.sha256}


class Run:
    def __init__(self, root: Path, start: str | None = None, end: str | None = None,
                 refresh: bool = False):
        self.root = root.resolve()
        settings = Settings.model_validate(yaml.safe_load((root / "configs/pipeline.yaml").read_text(encoding="utf-8")))
        self.settings = settings.model_dump()
        self.sources = yaml.safe_load((root / "configs/sources.yaml").read_text(encoding="utf-8"))
        self.start = date.fromisoformat(str(start or self.settings["start_date"]))
        self.end = date.fromisoformat(str(end or self.settings["end_date"]))
        if self.start > self.end:
            raise ValueError("Start date must not exceed end date")
        self.refresh = refresh
        self.metadata = self.root / "data/metadata"
        self.manifest_path = self.metadata / "downloads.json"
        self.state_path = self.metadata / "run.json"
        self.downloads = read_json(self.manifest_path, [])
        self.state = read_json(self.state_path, {"sources": {}, "datasets": {}, "quality": {}})
        self.host_times: dict[str, float] = {}
        verify = True
        if os.name == "nt":
            import ssl
            verify = ssl.create_default_context()
        self.http = httpx.Client(
            follow_redirects=True,
            timeout=httpx.Timeout(self.settings["timeout_seconds"], connect=8),
            headers={"User-Agent": "BSPB-FX-Control-Research/0.1"},
            verify=verify,
        )

    def path(self, relative: str) -> Path:
        candidate = (self.root / relative).resolve()
        if not candidate.is_relative_to(self.root):
            raise ValueError(f"Path outside the project: {relative}")
        return candidate

    def raw(self, source_id: str, key: str | None = None, url: str | None = None) -> list[Raw]:
        selected = {}
        for item in self.downloads:
            if item["source_id"] != source_id or (key is not None and item["key"] != key):
                continue
            if url is not None and item["url"] != url:
                continue
            selected[(item["key"], item["url"])] = item
        output = []
        for item in selected.values():
            path = self.path(item["path"])
            if not path.is_file() or digest(path) != item["sha256"]:
                raise SourceError(f"Raw file is missing or its SHA-256 has changed: {item['path']}")
            output.append(Raw(**{k: v for k, v in item.items() if k != "path"}, path=path))
        return output

    def _save(self, source_id: str, key: str, url: str, path: Path, sha256: str,
              size: int, method: str) -> Raw:
        item = {
            "key": key, "source_id": source_id, "url": url,
            "path": path.relative_to(self.root).as_posix(), "sha256": sha256,
            "size": size, "fetched_at": now(), "method": method,
        }
        prior = next((x for x in reversed(self.downloads)
                      if (x["source_id"], x["key"], x["url"]) == (source_id, key, url)), None)
        if prior is None or prior["sha256"] != sha256 or (
            method == "user_supplied" and prior["method"] != method
        ):
            self.downloads.append(item)
            write_json(self.manifest_path, self.downloads)
        else:
            item = prior
        return Raw(**{k: v for k, v in item.items() if k != "path"}, path=path)

    def import_raw(self, source_id: str, key: str, url: str, input_path: Path,
                   method: str = "user_supplied", suffix: str | None = None) -> Raw:
        suffix = suffix or input_path.suffix.lower()
        check_format(input_path, suffix)
        if source_id == "cuad" and key == "archive":
            if digest(input_path, "md5") != self.sources["cuad"]["md5"]:
                raise SourceError("CUAD archive does not match the Zenodo MD5")
        sha256 = digest(input_path)
        target = self.raw_target(source_id, sha256, suffix)
        if not target.exists():
            atomic_write(target, input_path.read_bytes())
        elif digest(target) != sha256:
            raise SourceError(f"Existing raw file has changed: {target.name}")
        return self._save(source_id, key, url, target, sha256, input_path.stat().st_size, method)

    def raw_target(self, source_id: str, sha256: str, suffix: str) -> Path:
        category = ("cbr" if source_id.startswith("cbr_") else
                    "bspb" if source_id.startswith("bspb_") else
                    "reference" if source_id == "case_workbook" else
                    "moex" if source_id == "moex" else "contracts")
        return self.root / "data/raw" / category / source_id / f"{sha256}{suffix}"

    def fetch(self, source_id: str, key: str, url: str, suffix: str,
              expected_md5: str | None = None) -> Raw:
        if not self.refresh:
            cached = self.raw(source_id, key, url)
            if cached:
                return cached[-1]
        parts = urlsplit(url)
        if parts.scheme != "https" or not parts.hostname:
            raise SourceError("Only HTTPS source URLs are supported")
        user_agent = {}
        if source_id == "sec":
            identity = os.environ.get("BSPB_SEC_USER_AGENT", "").strip()
            if "@" not in identity or " " not in identity:
                raise SourceError("SEC requires BSPB_SEC_USER_AGENT with organization and contact email",
                                  STATUS_RESTRICTED)
            user_agent["User-Agent"] = identity
        stage_dir = self.root / "data/interim"
        stage_dir.mkdir(parents=True, exist_ok=True)
        limit = int(self.settings["max_response_mib"]) * 1024**2
        interval = float(self.settings["minimum_request_interval"])
        if source_id == "sec":
            interval = max(interval, 0.5)
        for attempt in range(int(self.settings["attempts"])):
            sleep_for = self.host_times.get(parts.hostname, 0) + interval - time.monotonic()
            if sleep_for > 0:
                time.sleep(sleep_for)
            self.host_times[parts.hostname] = time.monotonic()
            delay = float(2**attempt)
            with NamedTemporaryFile(dir=stage_dir, delete=False, suffix=".part") as temporary:
                staged = Path(temporary.name)
                try:
                    LOG.info("GET %s %s", source_id, key)
                    with self.http.stream("GET", url, headers=user_agent) as response:
                        if response.status_code in (401, 403, 451):
                            raise SourceError(f"HTTP {response.status_code} for {key}", STATUS_RESTRICTED)
                        if response.status_code == 404:
                            raise SourceError(f"HTTP 404 for {key}", STATUS_ABSENT)
                        retry_after = response.headers.get("Retry-After")
                        if retry_after:
                            try:
                                delay = max(delay, float(retry_after))
                            except ValueError:
                                try:
                                    retry_date = parsedate_to_datetime(retry_after)
                                    delay = max(delay, (retry_date - datetime.now(timezone.utc)).total_seconds())
                                except (TypeError, ValueError, OverflowError):
                                    pass
                        response.raise_for_status()
                        received = 0
                        for chunk in response.iter_bytes():
                            received += len(chunk)
                            if received > limit:
                                raise SourceError(f"Payload exceeds configured size limit for {key}")
                            temporary.write(chunk)
                    temporary.close()
                    check_format(staged, suffix)
                    if expected_md5 and digest(staged, "md5") != expected_md5:
                        raise SourceError(f"Publisher checksum mismatch for {key}")
                    sha256 = digest(staged)
                    target = self.raw_target(source_id, sha256, suffix)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if not target.exists():
                        os.replace(staged, target)
                    elif digest(target) != sha256:
                        raise SourceError(f"Existing raw file has changed: {target.name}")
                    return self._save(source_id, key, url, target, sha256, received, "https")
                except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                    http_code = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None
                    retryable = http_code is None or http_code in (408, 425, 429) or http_code >= 500
                    if not retryable or attempt + 1 == self.settings["attempts"] or delay > 60:
                        status = STATUS_RESTRICTED if http_code == 429 else STATUS_UNVERIFIED
                        raise SourceError(f"{type(exc).__name__} for {key}: {exc}", status) from exc
                    LOG.warning("Retry %s/%s for %s in %.1f s: %s", attempt + 1,
                                self.settings["attempts"] - 1, key, delay, exc)
                finally:
                    temporary.close()
                    staged.unlink(missing_ok=True)
            time.sleep(delay)
        raise AssertionError("Configured number of attempts was exhausted")

    def source_result(self, source_id: str, status: str, detail: str = "") -> None:
        self.state["sources"][source_id] = {"status": status, "checked_at": now(), "detail": detail}
        self.save()

    def save(self) -> None:
        write_json(self.state_path, self.state)

    def close(self) -> None:
        self.http.close()
