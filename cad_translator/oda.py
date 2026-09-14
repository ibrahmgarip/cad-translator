from __future__ import annotations

import os
import shutil
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

import ezdxf


ODA_DOWNLOAD_URL = "https://www.opendesign.com/guestfiles/oda_file_converter"


class ODAFileConverterNotFound(RuntimeError):
    pass


def _runtime_roots() -> list[Path]:
    roots: list[Path] = []
    bundled_root = getattr(sys, "_MEIPASS", None)
    if bundled_root:
        roots.append(Path(bundled_root))
    if getattr(sys, "frozen", False):
        executable_dir = Path(sys.executable).resolve().parent
        roots.extend((executable_dir, executable_dir.parent.parent / "Resources"))
    roots.append(Path(__file__).resolve().parent.parent)
    return roots


def _unique(paths: list[Path]) -> list[Path]:
    unique: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = os.path.normcase(str(path))
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def oda_executable_candidates(
    platform_name: str | None = None,
    environ: Mapping[str, str] | None = None,
    runtime_roots: Sequence[Path] | None = None,
) -> list[Path]:
    """Return ODA executable candidates in priority order.

    Parameters are injectable to keep Windows path discovery testable on the
    macOS and Linux CI runners.
    """
    platform_name = platform_name or sys.platform
    environ = os.environ if environ is None else environ
    roots = list(runtime_roots) if runtime_roots is not None else _runtime_roots()
    candidates: list[Path] = []

    override = environ.get("CAD_TRANSLATOR_ODA_PATH", "").strip().strip('"')
    if override:
        candidates.append(Path(override).expanduser())

    if platform_name == "win32":
        for root in roots:
            candidates.extend(
                (
                    root / "ODAFileConverter.exe",
                    root / "ODAFileConverter" / "ODAFileConverter.exe",
                )
            )
        for variable in ("ProgramW6432", "ProgramFiles", "ProgramFiles(x86)"):
            program_files = environ.get(variable)
            if program_files:
                oda_root = Path(program_files) / "ODA"
                candidates.append(
                    oda_root / "ODAFileConverter" / "ODAFileConverter.exe"
                )
                candidates.extend(
                    sorted(
                        oda_root.glob("ODAFileConverter*/ODAFileConverter.exe"),
                        reverse=True,
                    )
                )
        path_match = shutil.which("ODAFileConverter.exe", path=environ.get("PATH"))
    elif platform_name == "darwin":
        for root in roots:
            candidates.append(
                root
                / "ODAFileConverter.app"
                / "Contents"
                / "MacOS"
                / "ODAFileConverter"
            )
        candidates.append(
            Path("/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter")
        )
        path_match = shutil.which("ODAFileConverter", path=environ.get("PATH"))
    else:
        path_match = shutil.which("ODAFileConverter", path=environ.get("PATH"))

    if path_match:
        candidates.append(Path(path_match))
    return _unique(candidates)


def configure_oda_converter(platform_name: str | None = None) -> Path | None:
    """Configure ezdxf for the first installed ODA File Converter found."""
    platform_name = platform_name or sys.platform
    option_name = "win_exec_path" if platform_name == "win32" else "unix_exec_path"
    for candidate in oda_executable_candidates(platform_name=platform_name):
        if candidate.is_file():
            ezdxf.options.set("odafc-addon", option_name, str(candidate))
            return candidate
    return None


def require_oda_converter():
    """Return ezdxf's ODA add-on or raise an actionable error."""
    from ezdxf.addons import odafc

    configure_oda_converter()
    if not odafc.is_installed():
        raise ODAFileConverterNotFound(
            "ODA File Converter is required for DWG files. Install it from "
            f"{ODA_DOWNLOAD_URL} or set CAD_TRANSLATOR_ODA_PATH to the full "
            "path of ODAFileConverter.exe. DXF files work without ODA."
        )
    return odafc
