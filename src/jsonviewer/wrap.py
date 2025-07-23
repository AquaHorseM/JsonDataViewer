from typing import List
import json

def pretty_lines(obj) -> List[str]:
    return json.dumps(obj, indent=2, ensure_ascii=False).splitlines()

def wrap_lines(lines: List[str], width: int, fold: bool) -> List[str]:
    out = []
    w = max(1, width - 1)
    if fold:
        for line in lines:
            out.append(line[:w-3] + '...' if len(line) > w else line)
    else:
        for line in lines:
            for i in range(0, len(line), w):
                out.append(line[i:i+w])
    return out
