#!/usr/bin/env python3
import sys, json, curses, collections, re
import ijson
import textwrap
from typing import Any, List, Tuple
from dataclasses import dataclass
from collections import deque

Path = Tuple[Any, ...]  # sequence of keys / indices

@dataclass
class Row:
    path: Path
    key: str            # rendered key (or index as str)
    value: Any
    depth: int
    is_container: bool

KEY_PATTERN = re.compile(r'("[^"]+":)')

class JSONViewer:
    def __init__(self, stdscr, filename):
        self.stdscr = stdscr
        self.filename = filename
        # state
        self.search_q = None
        self.matches = []
        self.match_idx = 0
        self.prev_buf = collections.deque(maxlen=3)
        self.index = 0
        self.top = 0
        # view modes
        self.key_mode = False
        self.fold_mode = False            # <<-- new fold mode
        # full-view storage
        self.wrapped = []
        self.raw_lines = []              # store unwrapped pretty lines
        # key-only mode state
        self.focus_path: Path = ()         # subtree root we’re viewing
        self.expanded: set[Path] = set()   # expanded nodes (paths)
        self.key_cursor = 0
        self.visible_rows: List[Row] = []  # flattened rows to render
        # initialize
        self.init_curses()
        self.open_gen()
        
    def get_obj_at(self, path: Path):
        obj = self.current
        for k in path:
            obj = obj[k]
        return obj
    
    def find_same_depth(self, rows, start_idx, depth, step):
        """Return next index at the same depth, or original if none."""
        i = start_idx + step
        while 0 <= i < len(rows):
            if rows[i].depth == depth:
                return i
            i += step
        return start_idx
    
    def first_child_index(self, rows, parent_path):
        plen = len(parent_path)
        for i, r in enumerate(rows):
            if len(r.path) == plen + 1 and r.path[:plen] == parent_path:
                return i
        return None
    
    def parent_index(self, rows, child_path):
        if not child_path:  # already root
            return None
        parent = child_path[:-1]
        for i, r in enumerate(rows):
            if r.path == parent:
                return i
        return None
    
    def iter_children(self, obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                yield k, v
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                yield i, v
        else:
            return
        
    def rebuild_visible(self):
        """Recompute the flat list of rows for key mode based on focus_path & expanded."""
        self.visible_rows = []
        root_obj = self.get_obj_at(self.focus_path)
        # depth of focus root is 0 on screen
        stack = [(self.focus_path, root_obj, 0)]
        # DFS over *visible* nodes only
        while stack:
            path, obj, depth = stack.pop()
            # Skip the root itself (we list its children, not itself) EXCEPT when focus_path == path == ()
            if path != self.focus_path:
                parent_path = path[:-1]
                key = str(path[-1])
                is_cont = isinstance(obj, (dict, list))
                self.visible_rows.append(Row(path, key, obj, depth, is_cont))
                # If not expanded or not container, do not push children
                if not (is_cont and path in self.expanded):
                    continue
            # push children in reverse to get natural order when popping
            if isinstance(obj, (dict, list)):
                children = list(self.iter_children(obj))
                for k, v in reversed(children):
                    stack.append((path + (k,), v, depth + (0 if path == self.focus_path else 1)))

    def init_curses(self):
        curses.curs_set(0)
        if curses.has_colors():
            curses.start_color()
            if hasattr(curses, 'use_default_colors'):
                curses.use_default_colors()
            try:
                curses.init_pair(1, curses.COLOR_CYAN, -1)
                self.key_attr = curses.color_pair(1) | curses.A_BOLD
                curses.init_pair(2, curses.COLOR_YELLOW, -1)
                self.match_attr = curses.color_pair(2) | curses.A_BOLD
            except curses.error:
                curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
                self.key_attr = curses.color_pair(1) | curses.A_BOLD
                curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
                self.match_attr = curses.color_pair(2) | curses.A_BOLD
        else:
            self.key_attr = curses.A_BOLD
            self.match_attr = curses.A_REVERSE

    def open_gen(self):
        if hasattr(self, 'f'):
            try: self.f.close()
            except: pass
        self.f = open(self.filename, 'r')
        self.gen = ijson.items(self.f, 'item')
        try:
            self.current = next(self.gen)
        except StopIteration:
            self.f.close()
            raise SystemExit("Error: JSON contains no items")
        self._prepare_current()

    def _prepare_current(self):
        # reset full view
        self.top = 0
        pretty = json.dumps(self.current, indent=2, ensure_ascii=False).splitlines()
        self.raw_lines = pretty
        self.wrapped = self.wrap_pretty(pretty)
        self.update_matches()
        # reset key mode lists
        self.keys = list(self.current.items()) if isinstance(self.current, dict) else []
        self.key_cursor = 0
        self.expanded.clear()

    def wrap_pretty(self, lines):
        h, w = self.stdscr.getmaxyx()
        width = w - 1
        wrapped = []
        for line in lines:
            # if fold_mode: show only first line without wrapping
            if self.fold_mode:
                if len(line) > width:
                    wrapped.append(line[:width-3] + '...')
                else:
                    wrapped.append(line)
            else:
                for i in range(0, len(line), width):
                    wrapped.append(line[i:i+width])
        return wrapped

    def update_matches(self):
        self.matches.clear()
        if not self.search_q:
            return
        try:
            pat = re.compile(self.search_q)
            is_regex = True
        except re.error:
            is_regex = False
        for r, line in enumerate(self.wrapped):
            if is_regex:
                for m in pat.finditer(line):
                    self.matches.append((r, m.start(), m.end()))
            else:
                start = 0
                while True:
                    idx = line.find(self.search_q, start)
                    if idx < 0: break
                    self.matches.append((r, idx, idx + len(self.search_q)))
                    start = idx + len(self.search_q)
        self.match_idx = 0

    def draw_full(self):
        self.stdscr.erase()
        h, w = self.stdscr.getmaxyx()
        width = w - 1
        for row in range(h - 1):
            if self.top + row < len(self.wrapped):
                line = self.wrapped[self.top + row]
                col = 0
                # highlight keys
                for m in KEY_PATTERN.finditer(line):
                    s, e = m.span(1)
                    self.stdscr.addstr(row, col, line[col:s])
                    self.stdscr.addstr(row, s, line[s:e], self.key_attr)
                    col = e
                self.stdscr.addstr(row, col, line[col:])
                # highlight search matches
                for i, (r, s, e) in enumerate(self.matches):
                    if r == self.top + row:
                        attr = self.match_attr
                        if i == self.match_idx:
                            attr |= curses.A_UNDERLINE
                        self.stdscr.chgat(row, s, e-s, attr)

    def draw_keys(self):
        self.stdscr.erase()
        h, w = self.stdscr.getmaxyx()
        width = w - 1
        row_screen = 0

        for idx, r in enumerate(self.visible_rows):
            if row_screen >= h - 2:
                break
            prefix = '  ' * r.depth
            marker = '▾ ' if (r.is_container and r.path in self.expanded) else ('▸ ' if r.is_container else '  ')
            key_txt = f"{prefix}{marker}{r.key}"
            # preview (collapsed containers or scalars)
            display_line = key_txt
            if not r.is_container or r.path not in self.expanded:
                try:
                    s = json.dumps(r.value, ensure_ascii=False)
                except Exception:
                    s = str(r.value)
                s = s.replace('\n', ' ')
                max_prev = width - len(display_line) - 2
                if max_prev > 0:
                    display_line = f"{display_line}: {s[:max_prev]}"

            # draw (highlight key text)
            # split: prefix+marker | key | rest
            start_key = len(prefix) + 2  # marker length always 2
            self.stdscr.addnstr(row_screen, 0, prefix + marker, width)
            # key highlighted
            self.stdscr.addnstr(row_screen, start_key, r.key, width - start_key, self.key_attr)
            rest_start = start_key + len(r.key)
            rest = display_line[rest_start:]
            if rest and rest_start < width:
                self.stdscr.addnstr(row_screen, rest_start, rest[:width-rest_start], width-rest_start)

            if idx == self.key_cursor:
                self.stdscr.chgat(row_screen, 0, min(len(display_line), width), curses.A_REVERSE)

            row_screen += 1

            # If expanded and container, show full JSON below (pretty, wrapped)
            if r.is_container and r.path in self.expanded:
                # already printed previews, but containers show their children separately,
                # so no value dump here.
                pass
            elif not r.is_container and r.path in self.expanded:
                # (Scalar values shouldn't be in expanded, but just in case)
                pass

        status = "Key Mode [↑/↓] move [Enter] toggle [→] zoom in [←] up [m] exit"
        self.stdscr.addnstr(h-1, 0, status.ljust(width), width, curses.A_REVERSE)


    def draw(self):
        if self.key_mode:
            self.draw_keys()
        else:
            self.draw_full()
            h, w = self.stdscr.getmaxyx()
            mode = 'Fold' if self.fold_mode else 'Full'
            status = (
                f"Item {self.index+1} prev {len(self.prev_buf)}/3 [{mode} View] "
                "[↑/↓ j/k] scroll [→] next [←] prev "
                "[/] search [n/N] nav [g] goto [f] fold [m] keys [q] quit"
            )[:w-1].ljust(w-1)
            self.stdscr.addnstr(h-1, 0, status, w-1, curses.A_REVERSE)

    def prompt(self, text):
        # unchanged
        h, w = self.stdscr.getmaxyx()
        curses.echo(); self.stdscr.addnstr(h-1, 0, text.ljust(w-1), w-1, curses.A_REVERSE)
        self.stdscr.refresh()
        inp = self.stdscr.getstr(h-1, len(text), w-1-len(text))
        curses.noecho(); return inp.decode(errors='ignore')

    def next_item(self):
        # unchanged
        try:
            self.prev_buf.append(self.current)
            self.current = next(self.gen)
            self.index += 1; self._prepare_current()
        except StopIteration:
            curses.flash()

    def prev_item(self):
        # unchanged
        if self.prev_buf:
            self.current = self.prev_buf.pop()
            self.index -= 1; self._prepare_current()
        else:
            curses.flash()

    def goto_item(self):
        # unchanged
        s = self.prompt("Jump to item #: ")
        try: tgt = int(s)-1
        except: curses.flash(); return
        self.open_gen(); self.prev_buf.clear(); self.index=0
        while self.index < tgt:
            self.prev_buf.append(self.current)
            try: self.current = next(self.gen)
            except: curses.flash(); break
            self.index += 1
        self._prepare_current()

    def search(self):
        # unchanged
        q = self.prompt("Search regex or text: ")
        self.search_q = q; self._prepare_current()

    def navigate_match(self, fwd=True):
        # unchanged
        if not self.matches: curses.flash(); return
        if fwd and self.match_idx < len(self.matches)-1: self.match_idx+=1
        elif not fwd and self.match_idx>0: self.match_idx-=1
        else: self.next_item() if fwd else self.prev_item(); return
        r, _, _ = self.matches[self.match_idx]
        h,_=self.stdscr.getmaxyx()
        if r<self.top: self.top=r
        elif r>=self.top+(h-1): self.top = r-(h-2)

    def toggle_key_mode(self):
        self.key_mode = not self.key_mode
        if self.key_mode:
            self.rebuild_visible()
            self.key_cursor = 0
        else:
            self.top = 0


    def loop(self):
        while True:
            self.draw()
            c = self.stdscr.getch()
            if c in (ord('q'),27): break
            if self.key_mode:
                row = self.visible_rows[self.key_cursor] if self.visible_rows else None
                if c in (curses.KEY_DOWN, ord('j')) and row:
                    self.key_cursor = self.find_same_depth(self.visible_rows, self.key_cursor, row.depth, +1)
                elif c in (curses.KEY_UP, ord('k')) and row:
                    self.key_cursor = self.find_same_depth(self.visible_rows, self.key_cursor, row.depth, -1)
                elif c in (ord('\n'), ord(' ')) and row:  # toggle expand/collapse
                    if row.is_container:
                        if row.path in self.expanded:
                            self.expanded.remove(row.path)
                        else:
                            self.expanded.add(row.path)
                        self.rebuild_visible()
                        # keep cursor on the same key if still visible
                        try:
                            self.key_cursor = next(i for i, r in enumerate(self.visible_rows) if r.path == row.path)
                        except StopIteration:
                            self.key_cursor = 0
                elif c == curses.KEY_RIGHT and row:
                    # go to value (first child) if container
                    if row.is_container:
                        self.expanded.add(row.path)
                        self.rebuild_visible()
                        idx = self.first_child_index(self.visible_rows, row.path)
                        if idx is not None:
                            self.key_cursor = idx
                elif c == curses.KEY_LEFT and row:
                    # go back to parent
                    pidx = self.parent_index(self.visible_rows, row.path)
                    if pidx is not None:
                        self.key_cursor = pidx
                    else:
                        # already root: collapse current if possible
                        if row.path in self.expanded:
                            self.expanded.remove(row.path)
                            self.rebuild_visible()
                            self.key_cursor = min(self.key_cursor, len(self.visible_rows)-1)
                elif c == ord('m'):
                    self.toggle_key_mode()

            else:
                if c == ord('/'):
                    self.search()
                elif c == ord('n'):
                    self.navigate_match(True)
                elif c == ord('N'):
                    self.navigate_match(False)
                elif c == curses.KEY_RIGHT:
                    self.next_item()
                elif c == curses.KEY_LEFT:
                    self.prev_item()
                elif c in (curses.KEY_DOWN, ord('j')):
                    self.top = min(self.top+1, max(0, len(self.wrapped)-(self.stdscr.getmaxyx()[0]-1)))
                elif c in (curses.KEY_UP, ord('k')):
                    self.top = max(self.top-1, 0)
                elif c == ord('g'):
                    self.goto_item()
                elif c == ord('m'):
                    self.toggle_key_mode()
                elif c == ord('f'):
                    # toggle fold mode
                    self.fold_mode = not self.fold_mode
                    self.wrapped = self.wrap_pretty(self.raw_lines)
                    self.update_matches()
        self.f.close()


def main(stdscr, filename):
    viewer = JSONViewer(stdscr, filename)
    viewer.loop()

if __name__ == '__main__':
    if len(sys.argv)!=2:
        print(f"Usage: {sys.argv[0]} big_list.json", file=sys.stderr)
        sys.exit(1)
    curses.wrapper(main, sys.argv[1])
