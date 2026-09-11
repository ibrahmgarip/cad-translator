from __future__ import annotations

from pathlib import Path
import os
import sys
import ezdxf
from ezdxf.entities import DXFEntity
from .models import TextItem

SUPPORTED = {"TEXT", "MTEXT", "ATTRIB", "ATTDEF", "MULTILEADER", "MLEADER"}


def _configure_oda_converter() -> None:
    """Point ezdxf's DWG add-on at the installed ODA converter."""
    candidates = [
        os.environ.get("CAD_TRANSLATOR_ODA_PATH", ""),
        str(Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "ODAFileConverter.app/Contents/MacOS/ODAFileConverter"),
        "/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            ezdxf.options.set("odafc-addon", "unix_exec_path", candidate)
            return

class DXFDocument:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        if self.path.suffix.lower() == ".dwg":
            _configure_oda_converter()
            from ezdxf.addons import odafc
            # R2013 keeps native MULTILEADER entities and is accepted by older
            # CAD readers that reject otherwise valid R2018 DXF files.
            self.doc = odafc.readfile(self.path, version="R2013", audit=True)
        else:
            self.doc = ezdxf.readfile(self.path)
        self.items: list[TextItem] = []
        self._entities: dict[str, DXFEntity] = {}

    @staticmethod
    def _get_text(entity: DXFEntity) -> str:
        typ = entity.dxftype()
        if typ == "MTEXT":
            return entity.text
        if typ in {"MULTILEADER", "MLEADER"}:
            if entity.has_mtext_content:
                return entity.get_mtext_content()
            return ""
        return entity.dxf.text

    @staticmethod
    def _set_text(entity: DXFEntity, value: str) -> None:
        typ = entity.dxftype()
        if typ == "MTEXT":
            entity.text = value
        elif typ in {"MULTILEADER", "MLEADER"}:
            entity.set_mtext_content(value)
        else:
            entity.dxf.text = value

    def scan(self) -> list[TextItem]:
        self.items.clear()
        self._entities.clear()
        # Querying the whole entity database includes modelspace, paperspace and block definitions.
        for entity in self.doc.entitydb.values():
            try:
                typ = entity.dxftype()
                if typ not in SUPPORTED:
                    continue
                text = self._get_text(entity)
                if not text or not text.strip():
                    continue
                handle = entity.dxf.handle
                layer = getattr(entity.dxf, "layer", "")
                item = TextItem(handle=handle, entity_type=typ, original=text, layer=layer)
                self.items.append(item)
                self._entities[handle] = entity
            except Exception:
                # A malformed non-critical entity should not abort the whole drawing scan.
                continue
        return self.items

    def apply(self, translations: dict[str, str]) -> int:
        changed = 0
        for handle, translated in translations.items():
            entity = self._entities.get(handle) or self.doc.entitydb.get(handle)
            if entity is None or not translated:
                continue
            if self._get_text(entity) != translated:
                self._set_text(entity, translated)
                changed += 1
        return changed

    def save_as(self, output_path: str | Path) -> Path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.suffix.lower() == ".dwg":
            _configure_oda_converter()
            from ezdxf.addons import odafc
            odafc.export_dwg(self.doc, output, version="R2013", audit=True, replace=True)
        else:
            self.doc.saveas(output)
        return output
