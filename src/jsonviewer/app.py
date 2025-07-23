# src/jsonviewer/app.py
"""
Core controller for the curses JSON viewer.

It wires together:
- state.py (ViewerState, Row, Path)
- loader.py (ItemLoader)
- wrap.py (pretty_lines, wrap_lines)
- search.py (build_matches)
- ui.full_view / ui.key_view (renderers)

Nothing here knows about argparse; see cli.py for the entry point.
"""

from __future__ import annotations

import curses
from collections import deque
from typing import Any, List, Optional

from .state import ViewerState, Row, Path
from .loader import ItemLoader
from .wrap import pretty_lines, wrap_lines
from .search import build_matches
from .ui.full_view import draw_full
from .ui.key_view import draw_keys


class JSONViewer:
    def __init__(self, stdscr, filename: str, count_total: bool = False, buffer_size: int = 30):
        self.stdscr = stdscr
        self.loader = ItemLoader(filename)
        self.state = ViewerState()
        self.state.prev_buf = deque(maxlen=buffer_size if buffer_size > 0 else None)
        self._init_curses()
        self._open_first_item()
        if count_total:
            self.loader.start_count_total()

    # ------------------------------------------------------------------ #
    # Initialization / teardown
    # ------------------------------------------------------------------ #
    def _init_curses(self) -> None:
        curses.curs_set(0)
        if curses.has_colors():
            curses.start_color()
            if hasattr(curses, "use_default_colors"):
                curses.use_default_colors()
            try:
                curses.init_pair(1, curses.COLOR_CYAN, -1)   # keys
                curses.init_pair(2, curses.COLOR_YELLOW, -1) # matches
            except curses.error:
                curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
                curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)

    def _open_first_item(self) -> None:
        self.loader.open()
        try:
            self.state.current = self.loader.next_item()
        except StopIteration:
            self.loader.close()
            raise SystemExit("Error: JSON contains no items")
        self.state.index = 0
        self.state.prev_buf.clear()
        self.state.fwd_buf.clear()
        self._prepare_current()

    # ------------------------------------------------------------------ #
    # Pure helpers (tree & navigation)
    # ------------------------------------------------------------------ #
    def _get_obj_at(self, path: Path) -> Any:
        obj = self.state.current
        for k in path:
            obj = obj[k]
        return obj

    @staticmethod
    def _iter_children(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                yield k, v
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                yield i, v

    def _rebuild_visible(self) -> None:
        """Recompute flat list of rows for key mode based on focus_path & expanded."""
        st = self.state
        st.visible_rows = []
        root_obj = self._get_obj_at(st.focus_path)
        stack: List[tuple[Path, Any, int]] = [(st.focus_path, root_obj, 0)]

        while stack:
            path, obj, depth = stack.pop()
            # Skip root itself (unless it's the absolute root)
            if path != st.focus_path:
                key = str(path[-1])
                is_cont = isinstance(obj, (dict, list))
                st.visible_rows.append(Row(path, key, obj, depth, is_cont))
                if not (is_cont and path in st.expanded):
                    continue

            if isinstance(obj, (dict, list)):
                children = list(self._iter_children(obj))
                for k, v in reversed(children):
                    stack.append((path + (k,), v, depth + (0 if path == st.focus_path else 1)))

    @staticmethod
    def _find_same_depth(rows: List[Row], start_idx: int, depth: int, step: int) -> int:
        i = start_idx + step
        while 0 <= i < len(rows):
            if rows[i].depth == depth:
                return i
            i += step
        return start_idx

    @staticmethod
    def _first_child_index(rows: List[Row], parent_path: Path) -> Optional[int]:
        plen = len(parent_path)
        for i, r in enumerate(rows):
            if len(r.path) == plen + 1 and r.path[:plen] == parent_path:
                return i
        return None

    @staticmethod
    def _parent_index(rows: List[Row], child_path: Path) -> Optional[int]:
        if not child_path:
            return None
        parent = child_path[:-1]
        for i, r in enumerate(rows):
            if r.path == parent:
                return i
        return None

    # ------------------------------------------------------------------ #
    # State updates when a new item is loaded or config changes
    # ------------------------------------------------------------------ #
    def _prepare_current(self) -> None:
        st = self.state
        st.top = 0
        st.raw_lines = pretty_lines(st.current)

        h, w = self.stdscr.getmaxyx()
        st.wrapped = wrap_lines(st.raw_lines, w, st.fold_mode)

        st.matches, st.match_idx = build_matches(st.wrapped, st.search_q)

        # prev buffer is managed elsewhere
        # key-mode resets
        st.focus_path = ()
        st.expanded.clear()
        st.key_cursor = 0
        st.visible_rows.clear()
        if st.key_mode:
            self._rebuild_visible()

    # ------------------------------------------------------------------ #
    # Rendering
    # ------------------------------------------------------------------ #
    def _draw(self) -> None:
        if self.state.total_count is None and self.loader.total_items is not None:
            self.state.total_count = self.loader.total_items
        if self.state.key_mode:
            draw_keys(self.stdscr, self.state)
        else:
            draw_full(self.stdscr, self.state)

    # ------------------------------------------------------------------ #
    # Prompt (blocking input line)
    # ------------------------------------------------------------------ #
    def _prompt(self, text: str) -> str:
        h, w = self.stdscr.getmaxyx()
        curses.echo()
        self.stdscr.addnstr(h - 1, 0, text.ljust(w - 1), w - 1, curses.A_REVERSE)
        self.stdscr.refresh()
        inp = self.stdscr.getstr(h - 1, len(text), w - 1 - len(text))
        curses.noecho()
        return inp.decode(errors="ignore")

    # ------------------------------------------------------------------ #
    # Item navigation
    # ------------------------------------------------------------------ #
    def _next_item(self) -> None:
        st = self.state
        # If we came from a prev, prefer forward stack
        if st.fwd_buf:
            st.prev_buf.append(st.current)
            st.current = st.fwd_buf.pop()          # last pushed is next
            st.index += 1
            self._prepare_current()
            return

        # normal streaming
        try:
            st.prev_buf.append(st.current)
            st.fwd_buf.clear()
            st.current = self.loader.next_item()
            st.index += 1
            self._prepare_current()
        except StopIteration:
            curses.flash()

    def _prev_item(self) -> None:
        st = self.state
        if st.prev_buf:
            st.fwd_buf.append(st.current)
            st.current = st.prev_buf.pop()
            st.index -= 1
            self._prepare_current()
        else:
            curses.flash()

    def _goto_item(self) -> None:
        s = self._prompt("Jump to item #: ")
        try:
            tgt = int(s) - 1
        except Exception:
            curses.flash(); return

        self.loader.open()
        st = self.state
        st.prev_buf.clear()
        st.fwd_buf.clear()
        st.index = 0
        try:
            st.current = self.loader.next_item()
        except StopIteration:
            curses.flash(); return

        while st.index < tgt:
            st.prev_buf.append(st.current)
            try:
                st.current = self.loader.next_item()
            except StopIteration:
                curses.flash(); break
            st.index += 1
        self._prepare_current()

    # ------------------------------------------------------------------ #
    # Search / matches
    # ------------------------------------------------------------------ #
    def _search(self) -> None:
        q = self._prompt("Search regex or text: ")
        self.state.search_q = q
        self._prepare_current()

    def _navigate_match(self, fwd: bool = True) -> None:
        st = self.state
        if not st.matches:
            curses.flash()
            return
        if fwd and st.match_idx < len(st.matches) - 1:
            st.match_idx += 1
        elif not fwd and st.match_idx > 0:
            st.match_idx -= 1
        else:
            # wrap to next/prev item
            self._next_item() if fwd else self._prev_item()
            return

        r, _, _ = st.matches[st.match_idx]
        h, _ = self.stdscr.getmaxyx()
        if r < st.top:
            st.top = r
        elif r >= st.top + (h - 1):
            st.top = r - (h - 2)

    # ------------------------------------------------------------------ #
    # Modes
    # ------------------------------------------------------------------ #
    def _toggle_key_mode(self) -> None:
        st = self.state
        st.key_mode = not st.key_mode
        if st.key_mode:
            self._rebuild_visible()
            st.key_cursor = 0
        else:
            st.top = 0

    def _toggle_fold_mode(self) -> None:
        st = self.state
        st.fold_mode = not st.fold_mode
        h, w = self.stdscr.getmaxyx()
        st.wrapped = wrap_lines(st.raw_lines, w, st.fold_mode)
        st.matches, st.match_idx = build_matches(st.wrapped, st.search_q)

    # ------------------------------------------------------------------ #
    # Main loop
    # ------------------------------------------------------------------ #
    def loop(self) -> None:
        try:
            while True:
                self._draw()
                c = self.stdscr.getch()

                # common quit
                if c in (ord("q"), 27):  # ESC
                    break

                st = self.state
                if st.key_mode:
                    # key-mode navigation
                    row = st.visible_rows[st.key_cursor] if st.visible_rows else None
                    if c in (curses.KEY_DOWN, ord("j")) and row:
                        st.key_cursor = self._find_same_depth(st.visible_rows, st.key_cursor, row.depth, +1)
                    elif c in (curses.KEY_UP, ord("k")) and row:
                        st.key_cursor = self._find_same_depth(st.visible_rows, st.key_cursor, row.depth, -1)
                    elif c in (ord('\n'), ord(' ')) and row:  # toggle expand/collapse
                        if row.path in st.expanded:
                            st.expanded.remove(row.path)
                        else:
                            st.expanded.add(row.path)
                        # Only rebuild the visible tree if it's a container (children list changes)
                        if row.is_container:
                            self._rebuild_visible()
                            try:
                                st.key_cursor = next(i for i, r in enumerate(st.visible_rows) if r.path == row.path)
                            except StopIteration:
                                st.key_cursor = 0
                    elif c == curses.KEY_RIGHT and row:
                        if row.is_container:
                            st.expanded.add(row.path)
                            self._rebuild_visible()
                            idx = self._first_child_index(st.visible_rows, row.path)
                            if idx is not None:
                                st.key_cursor = idx
                    elif c == curses.KEY_LEFT and row:
                        pidx = self._parent_index(st.visible_rows, row.path)
                        if pidx is not None:
                            st.key_cursor = pidx
                        else:
                            if row.path in st.expanded:
                                st.expanded.remove(row.path)
                                self._rebuild_visible()
                                st.key_cursor = min(st.key_cursor, len(st.visible_rows) - 1)
                    elif c == ord("m"):
                        self._toggle_key_mode()

                else:
                    # full-view mode
                    if c == ord("/"):
                        self._search()
                    elif c == ord("n"):
                        self._navigate_match(True)
                    elif c == ord("N"):
                        self._navigate_match(False)
                    elif c == curses.KEY_RIGHT:
                        self._next_item()
                    elif c == curses.KEY_LEFT:
                        self._prev_item()
                    elif c in (curses.KEY_DOWN, ord("j")):
                        max_top = max(0, len(st.wrapped) - (self.stdscr.getmaxyx()[0] - 1))
                        st.top = min(st.top + 1, max_top)
                    elif c in (curses.KEY_UP, ord("k")):
                        st.top = max(st.top - 1, 0)
                    elif c == ord("g"):
                        self._goto_item()
                    elif c == ord("m"):
                        self._toggle_key_mode()
                    elif c == ord("f"):
                        self._toggle_fold_mode()
        finally:
            self.loader.close()


# ---------------------------------------------------------------------- #
# Convenience function called by curses.wrapper in cli.py
# ---------------------------------------------------------------------- #
def run(stdscr, filename: str, count_total: bool = True, buffer_size: int = 3) -> None:
    viewer = JSONViewer(stdscr, filename, count_total=count_total, buffer_size=buffer_size)
    viewer.loop()