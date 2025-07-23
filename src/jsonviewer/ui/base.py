"""
Small shared helpers for UI code (safe drawing, status lines, etc.).
Import from full_view.py / key_view.py as needed.
"""

from __future__ import annotations
import curses
from typing import Iterable


def safe_addnstr(stdscr, y: int, x: int, s: str, n: int, attr: int = 0) -> None:
    """Never raise curses.error when drawing."""
    try:
        stdscr.addnstr(y, x, s, n, attr)
    except curses.error:
        pass


def safe_chgat(stdscr, y: int, x: int, n: int, attr: int) -> None:
    try:
        stdscr.chgat(y, x, n, attr)
    except curses.error:
        pass


def draw_status(stdscr, text: str) -> None:
    h, w = stdscr.getmaxyx()
    safe_addnstr(stdscr, h - 1, 0, text.ljust(w - 1), w - 1, curses.A_REVERSE)


def clamp(val: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, val))


def join_preview(parts: Iterable[str], max_len: int) -> str:
    """Join strings with spaces and truncate with ellipsis."""
    out = ""
    for p in parts:
        if not p:
            continue
        if out:
            cand = out + " " + p
        else:
            cand = p
        if len(cand) > max_len:
            return (cand[: max_len - 3] + "...") if max_len > 3 else cand[:max_len]
        out = cand
    return out
