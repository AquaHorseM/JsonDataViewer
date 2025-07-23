import curses
import re

from .base import safe_addnstr, safe_chgat, draw_status

KEY_PATTERN = re.compile(r'("[^"]+":)')

def draw_full(stdscr, state):
    stdscr.erase()
    h, w = stdscr.getmaxyx()
    width = w - 1

    for row in range(h - 1):
        idx = state.top + row
        if idx >= len(state.wrapped):
            break
        line = state.wrapped[idx]
        col = 0

        # Highlight JSON keys
        for m in KEY_PATTERN.finditer(line):
            s, e = m.span(1)
            safe_addnstr(stdscr, row, col, line[col:s], width - col)
            safe_addnstr(stdscr, row, s, line[s:e], width - s, curses.color_pair(1) | curses.A_BOLD)
            col = e
        # rest
        if col < len(line):
            safe_addnstr(stdscr, row, col, line[col:], width - col)

        # Highlight matches
        for i, (r, s, e) in enumerate(state.matches):
            if r == idx:
                attr = curses.color_pair(2) | curses.A_BOLD
                if i == state.match_idx:
                    attr |= curses.A_UNDERLINE
                safe_chgat(stdscr, row, s, e - s, attr)

    total = state.total_count if state.total_count is not None else "?"
    mode = "Fold" if state.fold_mode else "Full"
    maxlen = getattr(state.prev_buf, "maxlen", None)
    prev_info = f"{len(state.prev_buf)}/{maxlen if maxlen is not None else '∞'}"
    status = (
        f"Item {state.index+1}/{total} prev {prev_info} [{mode} View] "
        "[↑/↓ j/k] scroll [→] next [←] prev "
        "[/] search [n/N] nav [g] goto [f] fold [m] keys [q] quit"
    )[:w-1].ljust(w-1)
    draw_status(stdscr, status)
