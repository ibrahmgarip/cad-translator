import ezdxf
from ezdxf.math import Vec2
from ezdxf.render.mleader import ConnectionSide

from cad_translator.dxf_service import DXFDocument


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
