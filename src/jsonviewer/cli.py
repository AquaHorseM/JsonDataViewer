#!/usr/bin/env python3
from __future__ import annotations
import argparse, curses, sys
from pathlib import Path

from .app import run
from .config import (
    load_config, save_config, set_key, get_key,
    reset_config, DEFAULTS, config_path
)

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="jsonviewer", description="Curses JSON viewer")
    sub = p.add_subparsers(dest="cmd", required=False)

    # view/run (default)
    view = sub.add_parser("view", help="View a JSON/JSONL file (default command)")
    view.add_argument("file", nargs="?", help="Path to JSON/JSONL file (or - for stdin)")
    view.add_argument("--buffer-size", "-b", type=int, help="Override buffer size")
    view.add_argument("--no-count-total", dest="count_total", action="store_false",
                      help="Disable background total counting")
    view.set_defaults(count_total=None)  # None => load from config

    # config
    cfg = sub.add_parser("config", help="Get/set defaults")
    cfg_sub = cfg.add_subparsers(dest="cfg_cmd", required=True)

    cget = cfg_sub.add_parser("get", help="Get a key or entire config")
    cget.add_argument("key", nargs="?", help="Config key")

    cset = cfg_sub.add_parser("set", help="Set a key to value")
    cset.add_argument("key")
    cset.add_argument("value")

    cres = cfg_sub.add_parser("reset", help="Reset to factory defaults")

    cpath = cfg_sub.add_parser("path", help="Show config file path")

    return p

def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    # If user didn't type a subcommand (or typed a file first), prepend "view"
    if not argv or argv[0] not in {"view", "config"}:
        argv = ["view"] + argv

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "config":
        return handle_config(args)
    return handle_view(args, parser)

def handle_view(args, parser) -> int:
    if not args.file:
        parser.error("file is required (or use `jsonviewer config ...`)")

    cfg = load_config()
    buffer_size = args.buffer_size if args.buffer_size is not None else cfg["buffer_size"]
    count_total = cfg["count_total"] if args.count_total is None else args.count_total

    file_path = Path(args.file)
    if str(file_path) != "-" and not file_path.exists():
        print(f"Error: {file_path} not found", file=sys.stderr)
        return 1

    curses.wrapper(run, str(file_path), count_total, buffer_size)
    return 0

def handle_config(args) -> int:
    try:
        if args.cfg_cmd == "get":
            if args.key:
                print(get_key(args.key))
            else:
                for k, v in load_config().items():
                    print(f"{k} = {v}")
        elif args.cfg_cmd == "set":
            set_key(args.key, args.value)
            print(f"{args.key} set to {get_key(args.key)}")
        elif args.cfg_cmd == "reset":
            reset_config()
            print("Config reset to defaults.")
        elif args.cfg_cmd == "path":
            print(config_path())
    except KeyError as e:
        print(str(e), file=sys.stderr); return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
