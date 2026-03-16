"""Tests for the notebook CLI module."""

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from supernote.cli.notebook import (
    add_parser,
    convert_all,
    convert_and_concat_all,
    convert_to_pdf,
    convert_to_svg,
    convert_to_txt,
    parse_color,
    subcommand_analyze,
    subcommand_convert,
    subcommand_merge,
    subcommand_reconstruct,
)

# ---------------------------------------------------------------------------
# parse_color
# ---------------------------------------------------------------------------


def test_parse_color_valid() -> None:
    result = parse_color("black,#333333,#666666,white")
    assert len(result) == 4
    assert all(isinstance(v, int) for v in result)


def test_parse_color_wrong_count() -> None:
    with pytest.raises(ValueError, match="4 colors"):
        parse_color("black,white")


def test_parse_color_all_named() -> None:
    result = parse_color("black,black,white,white")
    assert len(result) == 4


# ---------------------------------------------------------------------------
# add_parser
# ---------------------------------------------------------------------------


def test_add_parser_registers_subcommands() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    add_parser(subparsers)
    # Verify that all expected subcommands are registered
    choices = subparsers.choices if hasattr(subparsers, "choices") else {}
    for cmd in ("analyze", "convert", "merge", "reconstruct"):
        assert cmd in choices


# ---------------------------------------------------------------------------
# convert_all
# ---------------------------------------------------------------------------


def test_convert_all_calls_save_for_each_page() -> None:
    converter = MagicMock()
    converter.convert.return_value = MagicMock()
    save_func = MagicMock()
    convert_all(converter, 3, "output.png", save_func, {})
    assert save_func.call_count == 3
    assert converter.convert.call_count == 3


def test_convert_all_zero_pages() -> None:
    converter = MagicMock()
    save_func = MagicMock()
    convert_all(converter, 0, "output.png", save_func, {})
    save_func.assert_not_called()


# ---------------------------------------------------------------------------
# convert_and_concat_all
# ---------------------------------------------------------------------------


def test_convert_and_concat_all_with_separator() -> None:
    converter = MagicMock()
    converter.convert.side_effect = ["page1", "page2"]
    save_func = MagicMock()
    convert_and_concat_all(converter, 2, "output.txt", save_func, "---")
    save_func.assert_called_once()
    call_data = save_func.call_args[0][0]
    assert "page1" in call_data
    assert "---" in call_data


def test_convert_and_concat_all_no_separator() -> None:
    converter = MagicMock()
    converter.convert.side_effect = ["page1", "page2"]
    save_func = MagicMock()
    convert_and_concat_all(converter, 2, "output.txt", save_func, None)
    save_func.assert_called_once()


def test_convert_and_concat_all_none_pages() -> None:
    """None pages are replaced with empty string."""
    converter = MagicMock()
    converter.convert.side_effect = [None, "page2"]
    save_func = MagicMock()
    convert_and_concat_all(converter, 2, "output.txt", save_func, None)
    save_func.assert_called_once()


def test_convert_and_concat_all_empty(capsys: pytest.CaptureFixture[str]) -> None:
    converter = MagicMock()
    save_func = MagicMock()
    convert_and_concat_all(converter, 0, "output.txt", save_func, None)
    save_func.assert_not_called()
    captured = capsys.readouterr()
    assert "no data" in captured.out


# ---------------------------------------------------------------------------
# subcommand_analyze
# ---------------------------------------------------------------------------


def test_subcommand_analyze(
    test_note_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    args = argparse.Namespace(input=str(test_note_path), policy="strict")
    subcommand_analyze(args)
    captured = capsys.readouterr()
    # Should print some JSON with metadata
    assert "{" in captured.out


# ---------------------------------------------------------------------------
# subcommand_reconstruct
# ---------------------------------------------------------------------------


def test_subcommand_reconstruct(test_note_path: Path, tmp_path: Path) -> None:
    output = str(tmp_path / "reconstructed.note")
    args = argparse.Namespace(input=str(test_note_path), output=output)
    subcommand_reconstruct(args)
    assert Path(output).exists()
    assert Path(output).stat().st_size > 0


# ---------------------------------------------------------------------------
# subcommand_merge (single file = reconstruct path)
# ---------------------------------------------------------------------------


def test_subcommand_merge_single_file(test_note_path: Path, tmp_path: Path) -> None:
    output = str(tmp_path / "merged.note")
    args = argparse.Namespace(input=[str(test_note_path)], output=output)
    subcommand_merge(args)
    assert Path(output).exists()


def test_subcommand_merge_two_files(test_note_path: Path, tmp_path: Path) -> None:
    output = str(tmp_path / "merged2.note")
    args = argparse.Namespace(
        input=[str(test_note_path), str(test_note_path)], output=output
    )
    subcommand_merge(args)
    assert Path(output).exists()


# ---------------------------------------------------------------------------
# subcommand_convert (png, txt)
# ---------------------------------------------------------------------------


def test_subcommand_convert_png_single(test_note_path: Path, tmp_path: Path) -> None:
    output = str(tmp_path / "page.png")
    args = argparse.Namespace(
        input=str(test_note_path),
        output=output,
        type="png",
        number=0,
        all=False,
        color=None,
        exclude_background=False,
        policy="strict",
    )
    subcommand_convert(args)
    assert Path(output).exists()


def test_subcommand_convert_txt_all(test_note_path: Path, tmp_path: Path) -> None:
    output = str(tmp_path / "notes.txt")
    args = argparse.Namespace(
        input=str(test_note_path),
        output=output,
        type="txt",
        number=0,
        all=True,
        color=None,
        text_page_separator="---",
        policy="strict",
    )
    subcommand_convert(args)


def test_subcommand_convert_invalid_color(
    test_note_path: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = str(tmp_path / "page.png")
    args = argparse.Namespace(
        input=str(test_note_path),
        output=output,
        type="png",
        number=0,
        all=False,
        color="notacolor,notacolor",  # invalid: only 2 values
        exclude_background=False,
        policy="strict",
    )
    with pytest.raises(SystemExit) as exc_info:
        subcommand_convert(args)
    assert exc_info.value.code == 1


def test_subcommand_convert_svg_single(test_note_path: Path, tmp_path: Path) -> None:
    output = str(tmp_path / "page.svg")
    args = argparse.Namespace(
        input=str(test_note_path),
        output=output,
        type="svg",
        number=0,
        all=False,
        color=None,
        exclude_background=False,
        policy="strict",
    )
    subcommand_convert(args)


def test_subcommand_convert_svg_all(test_note_path: Path, tmp_path: Path) -> None:
    output = str(tmp_path / "page.svg")
    args = argparse.Namespace(
        input=str(test_note_path),
        output=output,
        type="svg",
        number=0,
        all=True,
        color=None,
        exclude_background=True,
        policy="strict",
    )
    subcommand_convert(args)


def test_subcommand_convert_pdf_single(test_note_path: Path, tmp_path: Path) -> None:
    output = str(tmp_path / "page.pdf")
    args = argparse.Namespace(
        input=str(test_note_path),
        output=output,
        type="pdf",
        number=0,
        all=False,
        color=None,
        no_link=False,
        add_keyword=False,
        policy="strict",
    )
    subcommand_convert(args)
    assert Path(output).exists()


def test_subcommand_convert_pdf_all(test_note_path: Path, tmp_path: Path) -> None:
    output = str(tmp_path / "all.pdf")
    args = argparse.Namespace(
        input=str(test_note_path),
        output=output,
        type="pdf",
        number=0,
        all=True,
        color=None,
        no_link=True,
        add_keyword=True,
        policy="strict",
    )
    subcommand_convert(args)
    assert Path(output).exists()


def test_subcommand_convert_txt_single(test_note_path: Path, tmp_path: Path) -> None:
    output = str(tmp_path / "page.txt")
    args = argparse.Namespace(
        input=str(test_note_path),
        output=output,
        type="txt",
        number=0,
        all=False,
        color=None,
        text_page_separator="",
        policy="strict",
    )
    subcommand_convert(args)


def test_convert_to_svg_none_result(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """When SvgConverter returns None, 'no path data' is printed."""
    mock_notebook = MagicMock()
    converter = MagicMock()
    converter.convert.return_value = None
    with patch("supernote.cli.notebook.SvgConverter", return_value=converter):
        args = argparse.Namespace(
            output=str(tmp_path / "out.svg"),
            number=0,
            all=False,
            exclude_background=False,
        )
        convert_to_svg(args, mock_notebook, None)
    captured = capsys.readouterr()
    assert "no path data" in captured.out


def test_convert_to_pdf_none_result(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """When PdfConverter returns None, 'no data' is printed."""
    mock_notebook = MagicMock()
    converter = MagicMock()
    converter.convert.return_value = None
    with patch("supernote.cli.notebook.PdfConverter", return_value=converter):
        args = argparse.Namespace(
            output=str(tmp_path / "out.pdf"),
            number=0,
            all=False,
            no_link=False,
            add_keyword=False,
        )
        convert_to_pdf(args, mock_notebook, None)
    captured = capsys.readouterr()
    assert "no data" in captured.out


def test_convert_to_txt_none_result(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """When TextConverter returns None for a single page, 'no data' is printed."""
    mock_notebook = MagicMock()
    converter = MagicMock()
    converter.convert.return_value = None
    with patch("supernote.cli.notebook.TextConverter", return_value=converter):
        args = argparse.Namespace(
            output=str(tmp_path / "out.txt"),
            number=0,
            all=False,
        )
        convert_to_txt(args, mock_notebook, None)
    captured = capsys.readouterr()
    assert "no data" in captured.out
