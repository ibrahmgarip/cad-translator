from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from platformdirs import user_data_dir

from .text_utils import normalize_for_memory


class TranslationMemory:
    """Thread-safe SQLite-backed translation memory.

    A fresh SQLite connection is created for every operation so the same
    TranslationMemory instance can be used from Qt's UI and worker threads.

    The database lives in a user-writable data directory. If that location
    cannot be opened for any reason, we transparently fall back to a hidden
    directory in the user's home folder.
    """

    def __init__(self, db_path: str | Path | None = None):
        self._explicit_path = db_path is not None
        self.db_path = Path(db_path).expanduser() if db_path is not None else self._default_path()
        self._initialize()

    @staticmethod
    def _default_path() -> Path:
        override = os.environ.get("CAD_TRANSLATOR_DATA_DIR")
        if override:
            return Path(override).expanduser() / "translation_memory.sqlite3"
        return Path(user_data_dir("CAD Translator", "CAD Translator")) / "translation_memory.sqlite3"

    @staticmethod
    def _fallback_path() -> Path:
        return Path.home() / ".cad-translator" / "translation_memory.sqlite3"

    @staticmethod
    def _prepare_parent(path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.is_dir():
            raise RuntimeError(f"Translation memory path is a directory, not a file: {path}")

    def _open(self, path: Path) -> sqlite3.Connection:
        self._prepare_parent(path)
        conn = sqlite3.connect(str(path), timeout=30.0)
        try:
            conn.execute("PRAGMA busy_timeout = 30000")
            # A read-only database can be opened successfully but will fail
            # later during schema creation or a put(). Check writability while
            # the candidate path is being selected so fallback remains useful.
            conn.execute("BEGIN IMMEDIATE")
            conn.rollback()
        except Exception:
            conn.close()
            raise
        return conn

    def _connect(self) -> sqlite3.Connection:
        candidates = [self.db_path]
        if not self._explicit_path:
            fallback = self._fallback_path()
            if fallback != self.db_path:
                candidates.append(fallback)

        errors: list[tuple[Path, Exception]] = []
        for candidate in candidates:
            try:
                conn = self._open(candidate)
                self.db_path = candidate
                return conn
            except (OSError, RuntimeError, sqlite3.Error) as error:
                errors.append((candidate, error))

        if self._explicit_path:
            path, error = errors[0]
            raise sqlite3.OperationalError(
                f"Unable to open translation-memory database at {path}: {error}"
            ) from error

        details = "; ".join(f"{path}: {error}" for path, error in errors)
        raise sqlite3.OperationalError(
            "Unable to open the translation-memory database. "
            f"Tried {details}"
        ) from errors[-1][1]

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        """Open one connection for an operation and always release it."""
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _initialize(self) -> None:
        with self._connection() as conn:
            # WAL can fail on unusual/network filesystems; fall back to DELETE
            # journal mode without making translation memory unusable.
            try:
                conn.execute("PRAGMA journal_mode = WAL")
            except sqlite3.DatabaseError:
                conn.execute("PRAGMA journal_mode = DELETE")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS translations (
                    source_lang TEXT NOT NULL,
                    target_lang TEXT NOT NULL,
                    source_text TEXT NOT NULL,
                    translated_text TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(source_lang, target_lang, source_text)
                )
                """
            )

    def get(self, source_lang: str, target_lang: str, source_text: str) -> str | None:
        key = normalize_for_memory(source_text)
        with self._connection() as conn:
            row = conn.execute(
                "SELECT translated_text FROM translations "
                "WHERE source_lang=? AND target_lang=? AND source_text=?",
                (source_lang, target_lang, key),
            ).fetchone()
        return row[0] if row else None

    def put(self, source_lang: str, target_lang: str, source_text: str, translated_text: str) -> None:
        key = normalize_for_memory(source_text)
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO translations(source_lang, target_lang, source_text, translated_text)
                VALUES(?,?,?,?)
                ON CONFLICT(source_lang,target_lang,source_text)
                DO UPDATE SET
                    translated_text=excluded.translated_text,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (source_lang, target_lang, key, translated_text),
            )

    def close(self) -> None:
        pass
