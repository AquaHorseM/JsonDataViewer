import re
from typing import List, Tuple

def build_matches(lines: List[str], query: str | None) -> Tuple[List[tuple[int,int,int]], int]:
    if not query:
        return [], 0
    try:
        pat = re.compile(query)
        is_regex = True
    except re.error:
        is_regex = False

    matches = []
    for r, line in enumerate(lines):
        if is_regex:
            for m in pat.finditer(line):
                matches.append((r, m.start(), m.end()))
        else:
            start = 0
            while True:
                idx = line.find(query, start)
                if idx < 0:
                    break
                matches.append((r, idx, idx + len(query)))
                start = idx + len(query)
    return matches, 0
