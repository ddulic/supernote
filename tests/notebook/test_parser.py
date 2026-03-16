"""Tests for supernote.notebook.parser module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from supernote.notebook import fileformat
from supernote.notebook.parser import (
    SupernoteParser,
    SupernoteXParser,
    _get_bitmap_address,
    _get_cover_address,
)

# ---------------------------------------------------------------------------
# _get_cover_address
# ---------------------------------------------------------------------------


def test_get_cover_address_cover2() -> None:
    """COVER_2 key takes priority over COVER_1."""
    metadata = MagicMock()
    metadata.footer = {"COVER_2": "123", "COVER_1": "456"}
    assert _get_cover_address(metadata) == 123


def test_get_cover_address_cover1_only() -> None:
    """COVER_1 is used when COVER_2 is absent."""
    metadata = MagicMock()
    metadata.footer = {"COVER_1": "456"}
    assert _get_cover_address(metadata) == 456


# ---------------------------------------------------------------------------
# _get_bitmap_address
# ---------------------------------------------------------------------------


def test_get_bitmap_address_no_layers() -> None:
    """Non-layer-supported page reads from DATA key."""
    metadata = MagicMock()
    metadata.is_layer_supported.return_value = False
    metadata.pages = [{}, {"DATA": "500"}]
    result = _get_bitmap_address(metadata, 1)
    assert result == [500]


# ---------------------------------------------------------------------------
# SupernoteParser.parse_file
# ---------------------------------------------------------------------------


def test_parse_file_with_test_note(test_note_path: Path) -> None:
    """parse() opens the file and delegates to parse_stream."""
    parser = SupernoteXParser()
    metadata = parser.parse(str(test_note_path))
    assert metadata is not None
    assert metadata.header is not None


# ---------------------------------------------------------------------------
# SupernoteParser._get_page_addresses (lines 521, 523)
# ---------------------------------------------------------------------------


def test_get_page_addresses_single_string() -> None:
    """PAGE value as plain string returns a single-element list."""
    parser = SupernoteParser()
    footer: dict[str, str | list[str]] = {"PAGE": "100"}
    result = parser._get_page_addresses(footer)
    assert result == [100]


def test_get_page_addresses_list() -> None:
    """PAGE value as list returns multiple addresses."""
    parser = SupernoteParser()
    footer: dict[str, str | list[str]] = {"PAGE": ["100", "200"]}
    result = parser._get_page_addresses(footer)
    assert result == [100, 200]


# ---------------------------------------------------------------------------
# SupernoteParser._extract_parameters (duplicate keys)
# ---------------------------------------------------------------------------


def test_extract_parameters_duplicate_key_first_dup() -> None:
    """Second occurrence of a key converts value to a list."""
    parser = SupernoteParser()
    result = parser._extract_parameters("<KEY:A><KEY:B>")
    assert result["KEY"] == ["A", "B"]


def test_extract_parameters_duplicate_key_third_dup() -> None:
    """Third occurrence appends to an existing list."""
    parser = SupernoteParser()
    result = parser._extract_parameters("<KEY:A><KEY:B><KEY:C>")
    assert result["KEY"] == ["A", "B", "C"]


# ---------------------------------------------------------------------------
# SupernoteXParser._parse_footer_block (keywords / titles / links)
# ---------------------------------------------------------------------------


def test_parse_footer_block_sets_keywords_titles_links() -> None:
    """Keywords, titles, and links are stored in the footer dict."""
    parser = SupernoteXParser()
    fobj = MagicMock()

    with (
        patch.object(SupernoteParser, "_parse_metadata_block", return_value={}),
        patch.object(SupernoteXParser, "_get_keyword_addresses", return_value=[1]),
        patch.object(SupernoteXParser, "_parse_keyword_block", return_value={"K": "V"}),
        patch.object(SupernoteXParser, "_get_title_addresses", return_value=[2]),
        patch.object(SupernoteXParser, "_parse_title_block", return_value={"T": "V"}),
        patch.object(SupernoteXParser, "_get_link_addresses", return_value=[3]),
        patch.object(SupernoteXParser, "_parse_link_block", return_value={"L": "V"}),
    ):
        footer = parser._parse_footer_block(fobj, 0)

    assert fileformat.KEY_KEYWORDS in footer
    assert fileformat.KEY_TITLES in footer
    assert fileformat.KEY_LINKS in footer


# ---------------------------------------------------------------------------
# _get_keyword_addresses / _get_title_addresses / _get_link_addresses
# (single string value, not list)
# ---------------------------------------------------------------------------


def test_get_keyword_addresses_string_value() -> None:
    """KEYWORD_ key with string value appends a single int."""
    parser = SupernoteXParser()
    footer: dict[str, str | list[str]] = {"KEYWORD_0001ABCD": "100"}
    result = parser._get_keyword_addresses(footer)
    assert result == [100]


def test_get_title_addresses_string_value() -> None:
    """TITLE_ key with string value appends a single int."""
    parser = SupernoteXParser()
    footer: dict[str, str | list[str]] = {"TITLE_0001ABCD": "200"}
    result = parser._get_title_addresses(footer)
    assert result == [200]


def test_get_link_addresses_string_value() -> None:
    """LINK key with string value appends a single int."""
    parser = SupernoteXParser()
    footer: dict[str, str | list[str]] = {"LINKSITE_001": "300"}
    result = parser._get_link_addresses(footer)
    assert result == [300]
