from cad_translator.memory import TranslationMemory
from cad_translator.translation_service import TranslationService


class RecordingProvider:
    def __init__(self):
        self.calls = []

    def translate(self, texts, source_lang, target_lang):
        self.calls.append((texts, source_lang, target_lang))
        return [f"TR:{text}" for text in texts]


def test_identity_cache_entry_is_retranslated(tmp_path):
    memory = TranslationMemory(tmp_path / "tm.sqlite3")
    memory.put("ru", "tr", "ПОД ПОТОЛКОМ", "ПОД ПОТОЛКОМ")
    provider = RecordingProvider()

    result = TranslationService(provider, memory).translate_unique(
        ["ПОД ПОТОЛКОМ"], "ru", "tr", protect_tokens=False
    )

    assert result == {"ПОД ПОТОЛКОМ": "TR:ПОД ПОТОЛКОМ"}
    assert provider.calls == [(["ПОД ПОТОЛКОМ"], "ru", "tr")]
