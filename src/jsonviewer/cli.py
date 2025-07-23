#!/usr/bin/env python3
from __future__ import annotations

import argparse
import curses
import sys
from pathlib import Path

from .app import run


def positive_int(value: str) -> int:
    try:
        v = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be an integer")
    if v <= 0:
        raise argparse.ArgumentTypeError("must be > 0")
    return v


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="jsonviewer",
        description="Curses-based viewer for a JSON array / JSONL of items.",
    )
    p.add_argument("file", help="Path to a JSON file whose root is a list (or JSONL).")
    # cli.py
    p.add_argument("--jsonl", action="store_true", help="Force JSONL mode (one object per line)")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: {file_path} not found", file=sys.stderr)
        return 1
    curses.wrapper(run, str(file_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
