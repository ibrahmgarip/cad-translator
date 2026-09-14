from pathlib import Path

import ezdxf
import pytest

from cad_translator.oda import (
    ODAFileConverterNotFound,
    configure_oda_converter,
    oda_executable_candidates,
    require_oda_converter,
)


def test_windows_override_is_first_candidate(tmp_path):
    executable = tmp_path / "Custom ODA" / "ODAFileConverter.exe"
    candidates = oda_executable_candidates(
        platform_name="win32",
        environ={"CAD_TRANSLATOR_ODA_PATH": str(executable)},
        runtime_roots=[],
    )

    assert candidates[0] == executable


def test_windows_program_files_location_is_discovered(tmp_path):
    program_files = tmp_path / "Program Files"
    expected = program_files / "ODA" / "ODAFileConverter" / "ODAFileConverter.exe"
    candidates = oda_executable_candidates(
        platform_name="win32",
        environ={"ProgramFiles": str(program_files)},
        runtime_roots=[],
    )

    assert expected in candidates


def test_windows_versioned_program_files_location_is_discovered(tmp_path):
    program_files = tmp_path / "Program Files"
    expected = (
        program_files
        / "ODA"
        / "ODAFileConverter 26.9.0"
        / "ODAFileConverter.exe"
    )
    expected.parent.mkdir(parents=True)
    expected.write_bytes(b"")

    candidates = oda_executable_candidates(
        platform_name="win32",
        environ={"ProgramFiles": str(program_files)},
        runtime_roots=[],
    )

    assert expected in candidates


def test_windows_configuration_uses_win_exec_path(monkeypatch, tmp_path):
    executable = tmp_path / "ODAFileConverter.exe"
    executable.write_bytes(b"")
    configured: dict[tuple[str, str], str] = {}

    monkeypatch.setenv("CAD_TRANSLATOR_ODA_PATH", str(executable))
    monkeypatch.setattr(
        ezdxf.options,
        "set",
        lambda section, name, value: configured.__setitem__((section, name), value),
    )

    assert configure_oda_converter(platform_name="win32") == executable
    assert configured[("odafc-addon", "win_exec_path")] == str(executable)


def test_missing_oda_has_actionable_error(monkeypatch):
    from ezdxf.addons import odafc

    monkeypatch.setattr("cad_translator.oda.configure_oda_converter", lambda: None)
    monkeypatch.setattr(odafc, "is_installed", lambda: False)

    with pytest.raises(ODAFileConverterNotFound) as error:
        require_oda_converter()

    message = str(error.value)
    assert "CAD_TRANSLATOR_ODA_PATH" in message
    assert "DXF files work without ODA" in message
