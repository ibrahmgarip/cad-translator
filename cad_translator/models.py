from dataclasses import dataclass

@dataclass
class TextItem:
    handle: str
    entity_type: str
    original: str
    translated: str = ""
    layer: str = ""
    status: str = "pending"
