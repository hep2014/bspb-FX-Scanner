from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from filelock import FileLock

from data_pipeline.collect import GROUPS, collect
from data_pipeline.core import Run, SourceError
from data_pipeline.process import process
from data_pipeline.report import reports
from data_pipeline.validation.checks import validate


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(prog="python -m data_pipeline")
    cli.add_argument("--root", type=Path, default=Path.cwd())
    cli.add_argument("--start", help="Inclusive ISO date")
    cli.add_argument("--end", help="Inclusive ISO date")
    commands = cli.add_subparsers(dest="command", required=True)
    collector = commands.add_parser("collect")
    collector.add_argument("--source", action="append", help="Group or source ID, repeatable")
    collector.add_argument("--all", action="store_true")
    collector.add_argument("--refresh", action="store_true")
    importer = commands.add_parser("import-raw")
    importer.add_argument("--source", required=True)
    importer.add_argument("--key", required=True)
    importer.add_argument("--url", required=True)
    importer.add_argument("--file", type=Path, required=True)
    for command in ("process", "validate"):
        commands.add_parser(command).add_argument("--all", action="store_true")
    commands.add_parser("report")
    commands.add_parser("run").add_argument("--refresh", action="store_true")
    return cli


def main() -> int:
    cli = parser()
    args = cli.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        with FileLock(args.root / ".fx-data.lock", timeout=25):
            run = Run(args.root, args.start, args.end, getattr(args, "refresh", False))
            try:
                if args.command == "import-raw":
                    if args.source not in run.sources:
                        cli.error("unknown source ID")
                    raw = run.import_raw(args.source, args.key, args.url, args.file)
                    print(f"{raw.path} {raw.sha256}")
                elif args.command == "collect":
                    selected = list(GROUPS) if args.all else args.source
                    if not selected or any(source not in GROUPS and source not in run.sources for source in selected):
                        cli.error("provide --all or a known --source group or ID")
                    return int(collect(run, selected) > 0)
                elif args.command == "process":
                    process(run)
                elif args.command == "validate":
                    return int(validate(run) > 0)
                elif args.command == "report":
                    reports(run)
                elif args.command == "run":
                    failures = collect(run, list(GROUPS))
                    process(run)
                    errors = validate(run)
                    reports(run)
                    return int(failures > 0 or errors > 0)
            finally:
                run.close()
    except (OSError, SourceError, ValueError) as exc:
        logging.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
