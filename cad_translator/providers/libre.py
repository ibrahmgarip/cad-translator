from __future__ import annotations
import httpx
from .base import TranslationProvider

class LibreTranslateProvider(TranslationProvider):
    def __init__(self, base_url: str = "http://localhost:5000", api_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key.strip()

    def translate(self, texts: list[str], source_lang: str, target_lang: str) -> list[str]:
        results: list[str] = []
        with httpx.Client(timeout=60) as client:
            for text in texts:
                body = {"q": text, "source": source_lang, "target": target_lang, "format": "text"}
                if self.api_key:
                    body["api_key"] = self.api_key
                r = client.post(f"{self.base_url}/translate", json=body)
                r.raise_for_status()
                results.append(r.json()["translatedText"])
        return results
