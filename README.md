# CAD Translator

Desktop application for translating engineering text in DWG and DXF drawings.

CAD Translator preserves drawing geometry and text properties while translating:

- `TEXT`
- `MTEXT`
- `ATTRIB`
- `ATTDEF`
- `MULTILEADER` / `MLEADER`

DWG files use ODA File Converter internally. The user workflow is:

```text
Open DWG → scan → translate → review → save DWG
```

The original drawing is never overwritten unless the user selects the same output path.

## Requirements

- Python 3.11 or newer for source usage
- DeepL, Google Cloud Translation, or LibreTranslate credentials
- ODA File Converter for DWG support

DXF support works without ODA. macOS builds embed ODA File Converter. Windows users must install ODA File Converter and set `CAD_TRANSLATOR_ODA_PATH` if it is not on `PATH`.

Download ODA File Converter from the [Open Design Alliance](https://www.opendesign.com/GUESTFILES/ODA_FILE_CONVERTER).

## Run from source

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python run.py
```

Windows:

```bat
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python run.py
```

## Use

1. Click `Open CAD…` and select a `.dwg` or `.dxf` file.
2. Select source and target languages.
3. Select `DeepL`, `Google`, or `LibreTranslate`.
4. Enter the provider API key, or use `API Keys…` to save, replace, or clear keys.
5. Click `Translate`.
6. Review or edit translations.
7. Click `Save translated CAD…` and choose `.dwg` or `.dxf`.

API keys are stored in the operating system credential store (macOS Keychain,
Windows Credential Manager, or the platform equivalent). They are not written
to the repository or drawing.

## Glossary

Load CSV with `source,target` columns:

```csv
source,target
НАСОС,POMPA
КЛАПАН,VANA
ДАВЛЕНИЕ,BASINÇ
```

`resources/sample_glossary.csv` contains an example.

## Build macOS app

Install ODA File Converter at `/Applications/ODAFileConverter.app`, then run:

```bash
./build_macos.sh
```

Output:

```text
dist/CAD Translator.app
```

The build embeds ODA File Converter inside the application bundle. Code signing and notarization are required before broad distribution outside development machines.

This repository build uses ad-hoc signing when an Apple Developer ID certificate is not available. On macOS, if Gatekeeper still blocks the downloaded app, open it once with Control-click → `Open`, or run:

```bash
xattr -dr com.apple.quarantine "/Applications/CAD Translator.app"
```

For a release without this first-launch step, build with an Apple Developer ID certificate and notarize the ZIP.

## Tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

## License

MIT. See [LICENSE](LICENSE).
CAD Translator
