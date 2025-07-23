# src/jsonviewer/loader.py
from __future__ import annotations
import json, threading
from typing import Iterator, TextIO, Optional
import ijson

class ItemLoader:
    """
    Unified loader for JSON array or JSONL.
    Can optionally count items in a background thread.
    """
    def __init__(self, filename: str):
        self.filename = filename
        self._fh: Optional[TextIO] = None
        self._mode: str | None = None         # "array" or "jsonl"
        self._iter: Optional[Iterator] = None

        # counting
        self.total_items: Optional[int] = None
        self._count_thread: Optional[threading.Thread] = None

    # -------- open / iter -------- #
    def open(self) -> None:
        self.close()
        self._fh = open(self.filename, "r", encoding="utf-8")
        first_char = self._peek_first_non_ws(self._fh)
        if first_char == "[":
            self._mode = "array"
            self._iter = ijson.items(self._fh, "item")
        else:
            self._mode = "jsonl"
            self._iter = self._jsonl_iter(self._fh)

    def next_item(self):
        if self._iter is None:
            raise StopIteration
        return next(self._iter)

    def close(self) -> None:
        if self._fh:
            try:
                self._fh.close()
            finally:
                self._fh = None
                self._iter = None
                self._mode = None

    # -------- async count -------- #
    def start_count_total(self) -> None:
        """Kick off counting in a daemon thread (no-op if already running)."""
        if self._count_thread or self.total_items is not None:
            return

        def worker():
            try:
                if self._mode is None:
                    # ensure open() was called
                    self.open()
                    self.close()
                if self._mode == "jsonl":
                    self.total_items = self._count_jsonl()
                else:
                    self.total_items = self._count_array()
            except Exception:
                # fail silently; leave total_items=None
                pass

        self._count_thread = threading.Thread(target=worker, daemon=True)
        self._count_thread.start()

    def _count_jsonl(self) -> int:
        cnt = 0
        with open(self.filename, "r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    cnt += 1
        return cnt

    def _count_array(self) -> int:
        cnt = 0
        with open(self.filename, "r", encoding="utf-8") as fh:
            for _ in ijson.items(fh, "item"):
                cnt += 1
        return cnt

    # -------- helpers -------- #
    @staticmethod
    def _peek_first_non_ws(fh: TextIO) -> str:
        pos = fh.tell()
        while True:
            ch = fh.read(1)
            if ch == "":
                fh.seek(pos)
                return ""
            if not ch.isspace():
                fh.seek(pos)
                return ch

    @staticmethod
    def _jsonl_iter(fh: TextIO):
        for line in fh:
            s = line.strip()
            if not s:
                continue
            yield json.loads(s)
