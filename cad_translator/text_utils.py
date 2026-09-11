from __future__ import annotations

import re
from dataclasses import dataclass

# Tokens that should normally survive technical drawing translation unchanged.
_TOKEN_RE = re.compile(
    r"(?<!\w)(?:"
    r"DN\s?\d+(?:[xX]\d+)?|PN\s?\d+(?:\.\d+)?|"
    r"AISI\s?\d+[A-Z]?|"
    r"\d+(?:[.,]\d+)?\s?(?:mm|cm|m|km|kg|g|bar|kPa|MPa|Pa|°C|V|kV|A|Hz|kW|MW|L|l|m³/h|m3/h)|"
    r"[A-ZА-Я]{1,5}[-_/]\d+[A-ZА-Я0-9._/-]*|"
    r"Ø\s?\d+(?:[.,]\d+)?|"
    r"\b\d+(?:[.,]\d+)?\b"
    r")(?!\w)",
    re.IGNORECASE,
)

@dataclass
class ProtectedText:
    text: str
    tokens: dict[str, str]


def protect_technical_tokens(text: str) -> ProtectedText:
    tokens: dict[str, str] = {}

    def repl(match: re.Match[str]) -> str:
        key = f"__CADTOKEN_{len(tokens):04d}__"
        tokens[key] = match.group(0)
        return key

    return ProtectedText(_TOKEN_RE.sub(repl, text), tokens)


def restore_technical_tokens(text: str, tokens: dict[str, str]) -> str:
    for key, value in tokens.items():
        text = text.replace(key, value)
    return text


def normalize_for_memory(text: str) -> str:
    return " ".join(text.strip().split())
