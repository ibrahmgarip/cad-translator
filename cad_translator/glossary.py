from __future__ import annotations

import csv
from pathlib import Path

class Glossary:
    def __init__(self):
        self.entries: dict[str, str] = {}

    def load_csv(self, path: str | Path) -> int:
        self.entries.clear()
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            fields = {x.lower(): x for x in (reader.fieldnames or [])}
            src = fields.get("source") or fields.get("russian") or fields.get("ru")
            dst = fields.get("target") or fields.get("turkish") or fields.get("tr")
            if not src or not dst:
                raise ValueError("CSV must contain source,target columns (or russian,turkish / ru,tr).")
            for row in reader:
                s = (row.get(src) or "").strip()
                t = (row.get(dst) or "").strip()
                if s and t:
                    self.entries[s] = t
        return len(self.entries)

    def exact(self, text: str) -> str | None:
        return self.entries.get(text.strip())
