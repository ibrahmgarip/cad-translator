from __future__ import annotations

import keyring


SERVICE_NAME = "CAD Translator"
PROVIDERS = ("DeepL", "Google", "LibreTranslate")


class CredentialStore:
    """Store provider API keys in the operating system credential store."""

    def get(self, provider: str) -> str:
        return keyring.get_password(SERVICE_NAME, provider) or ""

    def set(self, provider: str, api_key: str) -> None:
        api_key = api_key.strip()
        if api_key:
            keyring.set_password(SERVICE_NAME, provider, api_key)
        else:
            self.delete(provider)

    def delete(self, provider: str) -> None:
        try:
            keyring.delete_password(SERVICE_NAME, provider)
        except keyring.errors.PasswordDeleteError:
            # Clearing an already empty field is intentionally idempotent.
            pass
