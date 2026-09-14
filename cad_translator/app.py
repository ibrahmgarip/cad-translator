from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton,
    QProgressBar, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QGroupBox,
    QGridLayout
)

from .dxf_service import DXFDocument
from .oda import ODAFileConverterNotFound
from .credentials import CredentialStore, PROVIDERS
from .glossary import Glossary
from .memory import TranslationMemory
from .providers import DeepLProvider, GoogleProvider, LibreTranslateProvider
from .translation_service import TranslationService

LANGS = {"Russian": "ru", "Turkish": "tr", "English": "en", "German": "de", "French": "fr"}

APP_STYLE = """
QWidget {
    font-size: 13px;
    color: #e6edf7;
}
QMainWindow, QWidget#centralWidget {
    background: #151a22;
}
QLabel#appTitle {
    color: #f5f7fb;
    font-size: 27px;
    font-weight: 700;
}
QLabel#appSubtitle, QLabel#muted {
    color: #9aa8ba;
}
QGroupBox {
    background: #1d2430;
    border: 1px solid #303b4c;
    border-radius: 10px;
    margin-top: 10px;
    padding: 18px 14px 14px;
    font-weight: 650;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
    color: #dce6f4;
}
QLineEdit, QComboBox {
    min-height: 32px;
    border: 1px solid #3b485b;
    border-radius: 6px;
    padding: 0 9px;
    background: #222b38;
    color: #e6edf7;
}
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #5d9bea;
}
QComboBox QAbstractItemView {
    background: #222b38;
    color: #e6edf7;
    selection-background-color: #315b91;
}
QPushButton {
    min-height: 32px;
    border: 1px solid #3b485b;
    border-radius: 6px;
    padding: 0 14px;
    background: #263140;
    color: #e6edf7;
}
QPushButton:hover { background: #303d4f; border-color: #5d7595; }
QPushButton#primaryButton {
    color: white;
    background: #2769c7;
    border-color: #2769c7;
    font-weight: 650;
}
QPushButton#primaryButton:hover { background: #1e58aa; }
QPushButton#saveButton {
    color: white;
    background: #218653;
    border-color: #218653;
    font-weight: 650;
}
QPushButton#saveButton:hover { background: #176b41; }
QTableWidget {
    border: 1px solid #303b4c;
    border-radius: 6px;
    background: #202834;
    alternate-background-color: #1c232e;
    gridline-color: #303b4c;
    selection-background-color: #315b91;
    selection-color: #f5f7fb;
}
QHeaderView::section {
    background: #293443;
    color: #c4d0df;
    border: 0;
    border-bottom: 1px solid #3b485b;
    padding: 8px;
    font-weight: 650;
}
QProgressBar {
    min-height: 8px;
    max-height: 8px;
    border: 0;
    border-radius: 4px;
    background: #303b4c;
    text-align: center;
}
QProgressBar::chunk { border-radius: 4px; background: #3978d4; }
"""

class TranslateWorker(QThread):
    done = Signal(dict)
    failed = Signal(str)

    def __init__(self, service, texts, source, target, protect):
        super().__init__()
        self.service = service
        self.texts = texts
        self.source = source
        self.target = target
        self.protect = protect

    def run(self):
        try:
            result = self.service.translate_unique(self.texts, self.source, self.target, self.protect)
            self.done.emit(result)
        except Exception as exc:
            self.failed.emit(f"{exc}\n\n{traceback.format_exc(limit=2)}")

class ScanWorker(QThread):
    done = Signal(object, object)
    failed = Signal(str)

    def __init__(self, path: str | Path):
        super().__init__()
        self.path = Path(path)

    def run(self):
        try:
            dxf = DXFDocument(self.path)
            self.done.emit(dxf, dxf.scan())
        except ODAFileConverterNotFound as exc:
            self.failed.emit(str(exc))
        except Exception as exc:
            self.failed.emit(f"{exc}\n\n{traceback.format_exc(limit=2)}")


class ApiKeysDialog(QDialog):
    def __init__(self, store: CredentialStore, parent=None):
        super().__init__(parent)
        self.setWindowTitle("API Keys")
        self.store = store
        self.fields: dict[str, QLineEdit] = {}
        form = QFormLayout(self)
        for provider in PROVIDERS:
            field = QLineEdit(store.get(provider))
            field.setEchoMode(QLineEdit.Password)
            field.setPlaceholderText(f"{provider} API key")
            self.fields[provider] = field
            form.addRow(f"{provider}:", field)

        help_text = QLabel("Keys are stored securely in your operating system's credential store.")
        help_text.setWordWrap(True)
        form.addRow(help_text)
        buttons = QHBoxLayout()
        clear = QPushButton("Clear all")
        clear.clicked.connect(self.clear_all)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save")
        save.setDefault(True)
        save.clicked.connect(self.save)
        buttons.addWidget(clear)
        buttons.addStretch(1)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        form.addRow(buttons)

    def clear_all(self):
        for field in self.fields.values():
            field.clear()

    def save(self):
        try:
            for provider, field in self.fields.items():
                self.store.set(provider, field.text())
        except Exception as exc:
            QMessageBox.critical(self, "API key error", f"Could not save API keys:\n{exc}")
            return
        self.accept()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CAD Translator")
        self.resize(1100, 720)
        self.dxf: DXFDocument | None = None
        self.glossary = Glossary()
        self.memory = TranslationMemory()
        self.credentials = CredentialStore()
        self.worker = None
        self.scan_worker = None
        self.translation_ready = False

        root = QWidget(); root.setObjectName("centralWidget"); self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(28, 22, 28, 24)
        layout.setSpacing(14)

        header = QVBoxLayout()
        title = QLabel("CAD Translator"); title.setObjectName("appTitle")
        subtitle = QLabel("Translate drawing text while keeping your CAD layout and formatting intact.")
        subtitle.setObjectName("appSubtitle")
        header.addWidget(title); header.addWidget(subtitle)
        layout.addLayout(header)

        file_box = QGroupBox("1. Choose a drawing")
        file_row = QHBoxLayout(file_box)
        self.file_edit = QLineEdit(); self.file_edit.setReadOnly(True)
        self.file_edit.setPlaceholderText("Select a DWG or DXF file to get started")
        browse = QPushButton("Browse…"); browse.setObjectName("primaryButton"); browse.clicked.connect(self.open_dxf)
        file_row.addWidget(self.file_edit, 1); file_row.addWidget(browse)
        layout.addWidget(file_box)

        options_box = QGroupBox("2. Translation settings")
        options = QGridLayout(options_box)
        options.setHorizontalSpacing(12); options.setVerticalSpacing(10)
        self.source_combo = QComboBox(); self.source_combo.addItems(LANGS.keys()); self.source_combo.setCurrentText("Russian")
        self.target_combo = QComboBox(); self.target_combo.addItems(LANGS.keys()); self.target_combo.setCurrentText("Turkish")
        self.engine_combo = QComboBox(); self.engine_combo.addItems(["DeepL", "Google", "LibreTranslate"])
        self.engine_combo.currentTextChanged.connect(self.engine_changed)
        self.api_key = QLineEdit(); self.api_key.setEchoMode(QLineEdit.Password); self.api_key.setPlaceholderText("Saved API key or enter one here")
        self.libre_url = QLineEdit("http://localhost:5000"); self.libre_url.setVisible(False)
        api_keys_btn = QPushButton("Manage API keys…"); api_keys_btn.clicked.connect(self.manage_api_keys)
        options.addWidget(QLabel("Translate from"), 0, 0); options.addWidget(self.source_combo, 0, 1)
        options.addWidget(QLabel("Translate to"), 0, 2); options.addWidget(self.target_combo, 0, 3)
        options.addWidget(QLabel("Service"), 1, 0); options.addWidget(self.engine_combo, 1, 1)
        options.addWidget(self.api_key, 1, 2); options.addWidget(api_keys_btn, 1, 3)
        options.addWidget(self.libre_url, 2, 2, 1, 2)
        self.protect_cb = QCheckBox("Protect technical tokens (DN100, P-101, Ø50…)"); self.protect_cb.setChecked(True)
        glossary_btn = QPushButton("Load glossary CSV…"); glossary_btn.clicked.connect(self.load_glossary)
        options.addWidget(self.protect_cb, 3, 0, 1, 3); options.addWidget(glossary_btn, 3, 3)
        layout.addWidget(options_box)

        actions = QHBoxLayout()
        self.scan_btn = QPushButton("Scan drawing"); self.scan_btn.clicked.connect(self.scan)
        self.translate_btn = QPushButton("Translate"); self.translate_btn.setObjectName("primaryButton"); self.translate_btn.clicked.connect(self.translate); self.translate_btn.setEnabled(False)
        self.save_btn = QPushButton("Save translated file…"); self.save_btn.setObjectName("saveButton")
        self.save_btn.clicked.connect(self.save); self.save_btn.setEnabled(False)
        actions.addWidget(self.scan_btn); actions.addWidget(self.translate_btn); actions.addStretch(1); actions.addWidget(self.save_btn)
        layout.addLayout(actions)

        results_box = QGroupBox("3. Review translations")
        results_layout = QVBoxLayout(results_box)
        self.status = QLabel("Choose a drawing to begin."); self.status.setObjectName("muted")
        self.progress = QProgressBar(); self.progress.setRange(0, 1); self.progress.setValue(0); self.progress.setVisible(False)
        results_layout.addWidget(self.status); results_layout.addWidget(self.progress)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Type", "Layer", "Handle", "Original", "Translation"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        results_layout.addWidget(self.table, 1)
        layout.addWidget(results_box, 1)
        self.engine_changed(self.engine_combo.currentText())

    def closeEvent(self, event):
        self.memory.close(); super().closeEvent(event)

    def engine_changed(self, name):
        self.libre_url.setVisible(name == "LibreTranslate")
        self.api_key.setPlaceholderText("Optional API key" if name == "LibreTranslate" else "API key")
        try:
            self.api_key.setText(self.credentials.get(name))
        except Exception as exc:
            self.api_key.clear()
            self.status.setText(f"Could not read saved API key: {exc}")

    def manage_api_keys(self):
        dialog = ApiKeysDialog(self.credentials, self)
        if dialog.exec() == QDialog.Accepted:
            self.engine_changed(self.engine_combo.currentText())

    def open_dxf(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open CAD", "", "CAD files (*.dxf *.dwg)"
        )
        if not path: return
        self.file_edit.setText(path)
        self.start_scan(path)

    def scan(self):
        path = self.file_edit.text().strip()
        if not path:
            return
        self.start_scan(path)

    def start_scan(self, path: str | Path):
        if self.scan_worker and self.scan_worker.isRunning():
            return
        self.dxf = None
        self.translation_ready = False
        self.save_btn.setEnabled(False)
        self.translate_btn.setEnabled(False)
        self.scan_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.status.setText("Scanning drawing…")
        self.scan_worker = ScanWorker(path)
        self.scan_worker.done.connect(self.scan_done)
        self.scan_worker.failed.connect(self.scan_failed)
        self.scan_worker.finished.connect(self.scan_finished)
        self.scan_worker.start()

    def scan_done(self, dxf, items):
        self.dxf = dxf
        self.table.setRowCount(len(items))
        for r, item in enumerate(items):
            values = [item.entity_type, item.layer, item.handle, item.original, item.translated]
            for c, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if c < 4: cell.setFlags(cell.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(r, c, cell)
        unique = len(set(x.original for x in items))
        self.status.setText(f"Found {len(items)} text entities / {unique} unique strings.")
        self.translate_btn.setEnabled(bool(items))

    def scan_failed(self, message):
        self.dxf = None
        QMessageBox.critical(self, "Open/scan failed", message)
        self.status.setText("Scan failed.")

    def scan_finished(self):
        self.progress.setVisible(False)
        self.scan_btn.setEnabled(True)
        self.scan_worker = None

    def load_glossary(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load glossary", "", "CSV files (*.csv)")
        if not path: return
        try:
            count = self.glossary.load_csv(path)
            self.status.setText(f"Loaded {count} glossary entries from {Path(path).name}.")
        except Exception as exc:
            QMessageBox.critical(self, "Glossary error", str(exc))

    def build_provider(self):
        name = self.engine_combo.currentText()
        key = self.api_key.text().strip()
        self.credentials.set(name, key)
        if name == "DeepL": return DeepLProvider(key)
        if name == "Google": return GoogleProvider(key)
        return LibreTranslateProvider(self.libre_url.text().strip(), key)

    def translate(self):
        if not self.dxf: return
        texts = [self.table.item(r, 3).text() for r in range(self.table.rowCount())]
        service = TranslationService(self.build_provider(), self.memory, self.glossary)
        self.translation_ready = False
        self.save_btn.setEnabled(False)
        self.translate_btn.setEnabled(False); self.progress.setVisible(True); self.progress.setRange(0, 0)
        self.status.setText("Translating unique strings…")
        self.worker = TranslateWorker(service, texts, LANGS[self.source_combo.currentText()], LANGS[self.target_combo.currentText()], self.protect_cb.isChecked())
        self.worker.done.connect(self.translation_done); self.worker.failed.connect(self.translation_failed); self.worker.start()

    def translation_done(self, result):
        for r in range(self.table.rowCount()):
            src = self.table.item(r, 3).text()
            self.table.item(r, 4).setText(result.get(src, ""))
        self.translation_ready = True
        self.save_btn.setEnabled(True)
        self.progress.setVisible(False); self.translate_btn.setEnabled(True)
        self.status.setText(f"Translated {len(result)} unique strings. Review/edit the Translation column, then save.")

    def translation_failed(self, message):
        self.progress.setVisible(False); self.translate_btn.setEnabled(True)
        QMessageBox.critical(self, "Translation failed", message)
        self.status.setText("Translation failed.")

    def save(self):
        if not self.dxf or not self.translation_ready:
            self.status.setText("Translate the drawing before saving.")
            return
        default = self.dxf.path.with_name(self.dxf.path.stem + "_tr_TR" + self.dxf.path.suffix.lower())
        path, _ = QFileDialog.getSaveFileName(
            self, "Save translated CAD", str(default), "CAD files (*.dxf *.dwg)"
        )
        if not path: return
        translations = {}
        for r in range(self.table.rowCount()):
            handle = self.table.item(r, 2).text()
            translated = self.table.item(r, 4).text().strip()
            if translated: translations[handle] = translated
        try:
            changed = self.dxf.apply(translations)
            self.dxf.save_as(path)
            # Save manual corrections into translation memory too.
            s = LANGS[self.source_combo.currentText()]; t = LANGS[self.target_combo.currentText()]
            for r in range(self.table.rowCount()):
                src = self.table.item(r, 3).text(); dst = self.table.item(r, 4).text().strip()
                if dst and dst != src: self.memory.put(s, t, src, dst)
            QMessageBox.information(self, "Saved", f"Saved {changed} translated entities to:\n{path}")
            self.status.setText(f"Saved: {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", str(exc))

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("CAD Translator")
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLE)
    w = MainWindow(); w.show()
    raise SystemExit(app.exec())

if __name__ == "__main__":
    main()
