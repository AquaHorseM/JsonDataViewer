# src/jsonviewer/ui/key_view.py
import curses, json
from .base import safe_addnstr, safe_chgat, draw_status
from ..wrap import pretty_lines, wrap_lines

# helper
def _scalar_is_long(val, avail_chars: int) -> bool:
    try:
        s = json.dumps(val, ensure_ascii=False)
    except Exception:
        s = str(val)
    return ("\n" in s) or (len(s) > max(0, avail_chars))

def draw_keys(stdscr, state):
    stdscr.erase()
    h, w = stdscr.getmaxyx()
    width = w - 1
    row_screen = 0
    rows = state.visible_rows

    for idx, r in enumerate(rows):
        if row_screen >= h - 2:
            break

        prefix = "  " * r.depth
        # how many chars remain after prefix + marker + key + ": "
        avail_prev = width - (len(prefix) + 2 + len(r.key) + 2)

        is_long_scalar = (not r.is_container) and _scalar_is_long(r.value, avail_prev)
        can_expand = r.is_container or is_long_scalar  # now scalars may expand too

        # choose marker
        if can_expand:
            if r.path in state.expanded:
                marker = "▾ "
            else:
                marker = "▸ " if r.is_container else "… "   # different icon for scalar
        else:
            marker = "  "

        key_txt = prefix + marker + r.key

        # collapsed preview?
        collapsed_preview = (not r.is_container) or (r.path not in state.expanded)
        display_line = key_txt
        if collapsed_preview:
            try:
                s = json.dumps(r.value, ensure_ascii=False)
            except Exception:
                s = str(r.value)
            s = s.replace("\n", " ")
            max_prev = width - len(display_line) - 2
            if max_prev > 0:
                display_line = f"{display_line}: {s[:max_prev]}"

        # draw the main row
        start_key = len(prefix) + 2
        safe_addnstr(stdscr, row_screen, 0, prefix + marker, width)
        safe_addnstr(stdscr, row_screen, start_key, r.key,
                     width - start_key, curses.color_pair(1) | curses.A_BOLD)
        rest_start = start_key + len(r.key)
        if rest_start < len(display_line):
            rest = display_line[rest_start:]
            if rest:
                safe_addnstr(stdscr, row_screen, rest_start, rest, width - rest_start)

        if idx == state.key_cursor:
            safe_chgat(stdscr, row_screen, 0, min(len(display_line), width), curses.A_REVERSE)

        row_screen += 1

        # expanded scalar: print full value under it
        if (r.path in state.expanded) and (not r.is_container):
            indent = "  " * (r.depth + 1)
            try:
                val_lines = pretty_lines(r.value)
            except Exception:
                val_lines = [str(r.value)]
            val_lines = wrap_lines([indent + ln for ln in val_lines], width, fold=False)

            for ln in val_lines:
                if row_screen >= h - 2:
                    break
                safe_addnstr(stdscr, row_screen, 0, ln, width)
                row_screen += 1

    status = "Key Mode  [↑/↓] same depth  [Enter] toggle  [→] child  [←] parent  [m] exit"
    draw_status(stdscr, status)
