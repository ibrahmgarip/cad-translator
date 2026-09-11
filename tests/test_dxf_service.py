import os

import ezdxf
from ezdxf.math import Vec2
from ezdxf.render.mleader import ConnectionSide

from cad_translator.dxf_service import DXFDocument, _isolated_oda_environment


def test_oda_environment_does_not_inherit_host_qt_paths(monkeypatch):
    monkeypatch.setattr("cad_translator.dxf_service.sys.platform", "darwin")
    monkeypatch.setenv("DYLD_LIBRARY_PATH", "/host/qt")
    monkeypatch.setenv("QT_PLUGIN_PATH", "/host/plugins")

    with _isolated_oda_environment():
        assert "DYLD_LIBRARY_PATH" not in os.environ
        assert "QT_PLUGIN_PATH" not in os.environ

    assert os.environ["DYLD_LIBRARY_PATH"] == "/host/qt"
    assert os.environ["QT_PLUGIN_PATH"] == "/host/plugins"


def test_multileader_mtext_is_scanned_and_replaced(tmp_path):
    doc = ezdxf.new("R2018")
    builder = doc.modelspace().add_multileader_mtext()
    builder.set_content("Под потолком")
    builder.add_leader_line(ConnectionSide.left, [(-10, 0), (0, 0)])
    builder.build(insert=Vec2(0, 0))
    path = tmp_path / "mleader.dxf"
    doc.saveas(path)

    drawing = DXFDocument(path)
    items = drawing.scan()
    mleaders = [item for item in items if item.entity_type == "MULTILEADER"]

    assert len(mleaders) == 1
    assert mleaders[0].original == "Под потолком"

    assert drawing.apply({mleaders[0].handle: "Tavan altında"}) == 1
    drawing.save_as(tmp_path / "translated.dxf")
    reloaded = DXFDocument(tmp_path / "translated.dxf")
    assert [item.original for item in reloaded.scan() if item.entity_type == "MULTILEADER"] == ["Tavan altında"]
