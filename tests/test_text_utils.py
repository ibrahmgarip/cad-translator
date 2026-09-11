from cad_translator.text_utils import protect_technical_tokens, restore_technical_tokens

def test_protect_restore():
    src = "НАСОС P-101 DN100 220V Ø50 AISI 304"
    p = protect_technical_tokens(src)
    assert "P-101" not in p.text
    assert "DN100" not in p.text
    assert restore_technical_tokens(p.text, p.tokens) == src
