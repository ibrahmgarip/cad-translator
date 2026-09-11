from __future__ import annotations
import httpx
from .base import TranslationProvider

class DeepLProvider(TranslationProvider):
    def __init__(self, api_key: str, base_url: str = "https://api-free.deepl.com"):
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")

    def translate(self, texts: list[str], source_lang: str, target_lang: str) -> list[str]:
        if not self.api_key:
            raise ValueError("DeepL API key is required.")
        # httpx 0.28 expects mapping-style form data. List-of-tuples is no
        # longer encoded as form fields and fails with "expected bytes-like
        # object, tuple found". A list value still produces repeated text
        # fields, as required by DeepL's API.
        data = {
            "text": texts,
            "source_lang": source_lang.upper(),
            "target_lang": target_lang.upper(),
        }
        with httpx.Client(timeout=60) as client:
            r = client.post(
                f"{self.base_url}/v2/translate",
                headers={"Authorization": f"DeepL-Auth-Key {self.api_key}"},
                data=data,
            )
            r.raise_for_status()
            payload = r.json()
        return [x["text"] for x in payload["translations"]]
