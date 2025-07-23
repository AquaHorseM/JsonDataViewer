from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Tuple, List, Set

Path = Tuple[Any, ...]  # sequence of keys / indices

@dataclass
class Row:
    path: Path
    key: str
    value: Any
    depth: int
    is_container: bool

@dataclass
class ViewerState:
    search_q: str | None = None
    matches: List[tuple[int,int,int]] = field(default_factory=list)
    match_idx: int = 0
    prev_buf: List[Any] = field(default_factory=list)
    index: int = 0
    top: int = 0
    key_mode: bool = False
    fold_mode: bool = False

    # key-mode specific
    focus_path: Path = ()
    expanded: Set[Path] = field(default_factory=set)
    key_cursor: int = 0
    visible_rows: List[Row] = field(default_factory=list)

    # current item
    current: Any = None
    raw_lines: List[str] = field(default_factory=list)
    wrapped: List[str] = field(default_factory=list)
