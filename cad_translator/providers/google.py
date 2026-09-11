from __future__ import annotations
import httpx
from .base import TranslationProvider

class GoogleProvider(TranslationProvider):
    """Google Cloud Translation Basic (v2) via API key."""
    def __init__(self, api_key: str):
        self.api_key = api_key.strip()

    def translate(self, texts: list[str], source_lang: str, target_lang: str) -> list[str]:
        if not self.api_key:
            raise ValueError("Google Cloud Translation API key is required.")
        body = {"q": texts, "source": source_lang, "target": target_lang, "format": "text"}
        with httpx.Client(timeout=60) as client:
            r = client.post(
                "https://translation.googleapis.com/language/translate/v2",
                params={"key": self.api_key},
                json=body,
            )
            r.raise_for_status()
            payload = r.json()
        return [x["translatedText"] for x in payload["data"]["translations"]]
