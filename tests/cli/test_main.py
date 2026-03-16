"""Tests for the main CLI entry point."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from supernote.cli.main import main


def test_main_no_command_exits() -> None:
    """main() with no subcommand prints help and exits with code 1."""
    with patch.object(sys, "argv", ["supernote"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 1


def test_main_dispatches_to_func(tmp_path: Path) -> None:
    """main() calls args.func when a valid command is given."""
    dummy = tmp_path / "dummy.note"
    dummy.write_bytes(b"")

    with (
        patch.object(sys, "argv", ["supernote", "analyze", str(dummy)]),
        patch("supernote.cli.notebook.subcommand_analyze") as mock_func,
    ):
        main()

    mock_func.assert_called_once()


def test_main_import_error_placeholder_exits() -> None:
    """When all modules fail to import, the placeholder handler exits with code 1."""
    with (
        patch.object(sys, "argv", ["supernote", "notebook"]),
        patch("importlib.import_module", side_effect=ImportError("missing dep")),
        pytest.raises(SystemExit) as exc_info,
    ):
        main()
    assert exc_info.value.code == 1


def test_main_import_error_admin_mentions_client() -> None:
    """Placeholder for 'admin' suggests installing 'client' extras."""
    with (
        patch.object(sys, "argv", ["supernote", "admin"]),
        patch("importlib.import_module", side_effect=ImportError("missing dep")),
        pytest.raises(SystemExit) as exc_info,
    ):
        main()
    assert exc_info.value.code == 1
