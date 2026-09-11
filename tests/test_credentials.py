from cad_translator.credentials import CredentialStore, SERVICE_NAME


def test_credentials_are_saved_and_cleared(monkeypatch):
    values = {}
    monkeypatch.setattr("cad_translator.credentials.keyring.set_password", lambda service, user, value: values.__setitem__((service, user), value))
    monkeypatch.setattr("cad_translator.credentials.keyring.get_password", lambda service, user: values.get((service, user)))
    monkeypatch.setattr("cad_translator.credentials.keyring.delete_password", lambda service, user: values.pop((service, user)))

    store = CredentialStore()
    store.set("DeepL", "  secret-key  ")
    assert store.get("DeepL") == "secret-key"
    assert values[(SERVICE_NAME, "DeepL")] == "secret-key"

    store.set("DeepL", "")
    assert store.get("DeepL") == ""
