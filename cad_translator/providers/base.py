from __future__ import annotations
from abc import ABC, abstractmethod

class TranslationProvider(ABC):
    @abstractmethod
    def translate(self, texts: list[str], source_lang: str, target_lang: str) -> list[str]:
        raise NotImplementedError
