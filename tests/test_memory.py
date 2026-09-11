from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from cad_translator.memory import TranslationMemory


def test_memory_roundtrip(tmp_path):
    tm = TranslationMemory(tmp_path / "tm.sqlite3")
    tm.put("ru", "tr", "  НАСОС   СТАНЦИЯ ", "POMPA İSTASYONU")
    assert tm.get("ru", "tr", "НАСОС СТАНЦИЯ") == "POMPA İSTASYONU"
    tm.close()


def test_memory_can_be_used_from_another_thread(tmp_path):
    """Regression test for the Qt QThread sqlite3.ProgrammingError."""
    tm = TranslationMemory(tmp_path / "tm.sqlite3")

    def worker():
        tm.put("ru", "tr", "ДАВЛЕНИЕ", "BASINÇ")
        return tm.get("ru", "tr", "ДАВЛЕНИЕ")

    with ThreadPoolExecutor(max_workers=1) as executor:
        assert executor.submit(worker).result() == "BASINÇ"

    # The same instance must still work from the creating/main thread afterwards.
    assert tm.get("ru", "tr", "ДАВЛЕНИЕ") == "BASINÇ"


def test_default_memory_directory_can_be_overridden(monkeypatch, tmp_path):
    monkeypatch.setenv("CAD_TRANSLATOR_DATA_DIR", str(tmp_path / "app-data"))
    tm = TranslationMemory()
    tm.put("ru", "tr", "НАСОС", "POMPA")
    assert tm.get("ru", "tr", "НАСОС") == "POMPA"
    assert tm.db_path.parent == tmp_path / "app-data"
    assert tm.db_path.exists()


def test_missing_database_parent_is_created(tmp_path):
    db_path = tmp_path / "nested" / "memory" / "translation.sqlite3"

    tm = TranslationMemory(db_path)

    assert db_path.parent.is_dir()
    tm.put("ru", "tr", "НАСОС", "POMPA")
    assert tm.get("ru", "tr", "НАСОС") == "POMPA"


def test_unavailable_primary_location_uses_fallback(monkeypatch, tmp_path):
    primary = tmp_path / "primary" / "translation_memory.sqlite3"
    fallback = tmp_path / "fallback" / "translation_memory.sqlite3"
    monkeypatch.setenv("CAD_TRANSLATOR_DATA_DIR", str(primary.parent))
    monkeypatch.setattr(TranslationMemory, "_fallback_path", staticmethod(lambda: fallback))

    original_prepare = TranslationMemory._prepare_parent

    def fail_primary(path: Path):
        if path == primary:
            raise PermissionError("primary unavailable")
        original_prepare(path)

    monkeypatch.setattr(TranslationMemory, "_prepare_parent", staticmethod(fail_primary))
    tm = TranslationMemory()

    assert tm.db_path == fallback
    tm.put("ru", "tr", "ДАВЛЕНИЕ", "BASINÇ")
    assert tm.get("ru", "tr", "ДАВЛЕНИЕ") == "BASINÇ"


def test_concurrent_memory_access_is_safe(tmp_path):
    tm = TranslationMemory(tmp_path / "tm.sqlite3")

    def worker(index):
        source = f"TEXT {index % 8}"
        tm.put("ru", "tr", source, f"METİN {index % 8}")
        return tm.get("ru", "tr", source)

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(worker, range(64)))

    assert all(result in {f"METİN {index}" for index in range(8)} for result in results)
