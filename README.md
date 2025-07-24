# JsonDataViewer

A fast, curses-based viewer for **huge JSON arrays / JSONL files**. It streams items with `ijson`, lets you search and jump between matches, and provides a **key-only tree mode** with expandable scalars and containers.

---

## Features

- **Stream large files**: load one top-level item at a time (`ijson.items(..., "item")`).
- **Two views**  
  - **Full view**: pretty-printed JSON with regex/text highlight.  
  - **Key mode**: tree of keys/indices; expand dicts, lists **and long scalars**.
- **Search & navigate**: `/` to search (regex or plain), `n/N` move between matches (wraps to next/prev item).
- **Jump & history**: `g` jump to item number; limited back buffer to keep it lightweight.
- **Fold mode**: truncate long lines for quick scanning.

---

## Install

```bash
git clone https://github.com/AquaHorseM/JsonDataViewer.git
cd JsonDataViewer

# Activate your environment. This repo is very lightweight so would fit in most existing environments.
# Or you may create a new one.
pip install -e .
```

---

## Usage

```bash
# Basic (opens viewer; same as `jsonviewer view …`)
jsonviewer path/to/big_list.json

# Explicit sub‑command (identical)
jsonviewer view path/to/big_list.json

# Override history buffer (keep last 10 items in memory)
jsonviewer view --buffer-size 10 path/to/big_list.json

# Disable background total‑item counting
jsonviewer view --no-count-total path/to/big_list.json
```

---

## Managing Defaults

```bash
# Show all current defaults
jsonviewer config get

# Show a single key
jsonviewer config get buffer_size

# Set a default (persists in ~/.config/jsonviewer/config.toml)
jsonviewer config set buffer_size 20
jsonviewer config set count_total false

# Reset everything to factory defaults
jsonviewer config reset

# Where the config file lives
jsonviewer config path
```

---

## Key Bindings

### Full View

| Key                | Action                                     |
|--------------------|---------------------------------------------|
| `↑` / `↓` or `j/k` | Scroll                                      |
| `→` / `←`          | Next / previous top-level item              |
| `/`                | Search (regex or plain text)                |
| `n` / `N`          | Next / previous match (wrap across items)   |
| `g`                | Jump to item number                         |
| `f`                | Toggle fold mode                            |
| `m`                | Enter key mode                              |
| `q` / `ESC`        | Quit                                        |

### Key Mode

| Key                    | Action                                             |
|------------------------|----------------------------------------------------|
| `↑` / `↓` or `j/k`     | Move to next/prev **row at same depth**            |
| `Enter` / `Space`      | Toggle expand/collapse (containers **or scalars**) |
| `→`                    | Jump to first child (if container)                 |
| `←`                    | Jump back to parent                                |
| `m`                    | Exit key mode                                      |
| `q` / `ESC`            | Quit                                               |

**Markers:**

- `▸` / `▾` : collapsed / expanded containers (dict/list)  
- `…` / `▾` : collapsed / expanded long scalar values  
- Two spaces: short, non-expandable scalars
