import httpx
from urllib.parse import parse_qs

from cad_translator.providers.deepl import DeepLProvider


def test_deepl_provider_encodes_batch_as_form_data(monkeypatch):
    captured = {}

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, **kwargs):
            request = httpx.Request("POST", url, data=kwargs["data"])
            captured["content"] = request.read()
            return httpx.Response(
                200,
                json={"translations": [{"text": "POMPA"}, {"text": "BASINÇ"}]},
                request=request,
            )

    monkeypatch.setattr("cad_translator.providers.deepl.httpx.Client", FakeClient)
    result = DeepLProvider("test-key").translate(["НАСОС", "ДАВЛЕНИЕ"], "ru", "tr")

    assert result == ["POMPA", "BASINÇ"]
    assert parse_qs(captured["content"].decode()) == {
        "text": ["НАСОС", "ДАВЛЕНИЕ"],
        "source_lang": ["RU"],
        "target_lang": ["TR"],
    }
