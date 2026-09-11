from __future__ import annotations
from collections import defaultdict
from .glossary import Glossary
from .memory import TranslationMemory
from .providers.base import TranslationProvider
from .text_utils import protect_technical_tokens, restore_technical_tokens

class TranslationService:
    def __init__(self, provider: TranslationProvider, memory: TranslationMemory, glossary: Glossary | None = None):
        self.provider = provider
        self.memory = memory
        self.glossary = glossary or Glossary()

    def translate_unique(self, texts: list[str], source_lang: str, target_lang: str, protect_tokens: bool = True) -> dict[str, str]:
        unique = list(dict.fromkeys(texts))
        result: dict[str, str] = {}
        to_translate: list[str] = []
        protected_lookup: dict[str, tuple[str, dict[str, str]]] = {}

        for source in unique:
            glossary_hit = self.glossary.exact(source)
            if glossary_hit is not None:
                result[source] = glossary_hit
                self.memory.put(source_lang, target_lang, source, glossary_hit)
                continue
            cached = self.memory.get(source_lang, target_lang, source)
            # An earlier save could store source text as its own translation
            # when the user saved before translation finished. Do not treat
            # that identity entry as a valid cache hit.
            if cached is not None and cached != source:
                result[source] = cached
                continue
            if protect_tokens:
                p = protect_technical_tokens(source)
                to_translate.append(p.text)
                protected_lookup[p.text] = (source, p.tokens)
            else:
                to_translate.append(source)
                protected_lookup[source] = (source, {})

        # Keep request sizes conservative and provider-independent.
        batch_size = 40
        for i in range(0, len(to_translate), batch_size):
            batch = to_translate[i:i + batch_size]
            translated_batch = self.provider.translate(batch, source_lang, target_lang)
            if len(translated_batch) != len(batch):
                raise RuntimeError("Translation provider returned an unexpected number of results.")
            for sent, translated in zip(batch, translated_batch):
                original, tokens = protected_lookup[sent]
                final = restore_technical_tokens(translated, tokens)
                result[original] = final
                self.memory.put(source_lang, target_lang, original, final)
        return result
