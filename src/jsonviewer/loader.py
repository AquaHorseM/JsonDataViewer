# src/jsonviewer/loader.py
from __future__ import annotations
import io
import json
from typing import Iterator, TextIO, Optional

import ijson


class ItemLoader:
    """
    Unified loader:
    - If file starts with '[' (after whitespace): treat as JSON array, stream with ijson.
    - Else: treat as JSONL (one JSON object per line).
    """
    def __init__(self, filename: str):
        self.filename = filename
        self._fh: Optional[TextIO] = None
        self._mode: str | None = None           # "array" or "jsonl"
        self._iter: Optional[Iterator] = None

    def open(self) -> None:
        self.close()
        self._fh = open(self.filename, 'r', encoding='utf-8')
        # Peek first non-space char
        first_char = self._peek_first_non_ws(self._fh)
        if first_char == '[':
            self._mode = "array"
            self._iter = ijson.items(self._fh, 'item')
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

    # ------------------ helpers ------------------ #
    @staticmethod
    def _peek_first_non_ws(fh: TextIO) -> str:
        pos = fh.tell()
        while True:
            ch = fh.read(1)
            if ch == '':
                fh.seek(pos)
                return ''  # empty file
            if not ch.isspace():
                fh.seek(pos)
                return ch

    @staticmethod
    def _jsonl_iter(fh: TextIO):
        for line in fh:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)
