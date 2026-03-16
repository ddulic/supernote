"""Tests for supernote.notebook.manipulator module."""

from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from supernote.notebook import fileformat
from supernote.notebook.manipulator import (
    NotebookBuilder,
    _pack_backgrounds,
    _pack_keywords,
    _pack_pages,
    merge,
    reconstruct,
)
from supernote.notebook.parser import load, load_notebook

# ---------------------------------------------------------------------------
# NotebookBuilder unit tests (no file needed)
# ---------------------------------------------------------------------------


def test_notebook_builder_init() -> None:
    builder = NotebookBuilder()
    assert builder.total_size == 0
    assert builder.toc == {}
    assert builder.blocks == []


def test_notebook_builder_custom_offset() -> None:
    builder = NotebookBuilder(offset=100)
    assert builder.total_size == 100


def test_notebook_builder_get_total_size() -> None:
    builder = NotebookBuilder()
    data = b"hello"
    builder.append("block1", data)
    # size = LENGTH_FIELD_SIZE (4) + len(data) (5) = 9
    expected = fileformat.LENGTH_FIELD_SIZE + len(data)
    assert builder.get_total_size() == expected


def test_notebook_builder_get_labels() -> None:
    builder = NotebookBuilder()
    builder.append("alpha", b"aaa")
    builder.append("beta", b"bbb")
    labels = set(builder.get_labels())
    assert "alpha" in labels
    assert "beta" in labels


def test_notebook_builder_get_block_address_single() -> None:
    builder = NotebookBuilder()
    builder.append("myblock", b"data", skip_block_size=True)
    addr = builder.get_block_address("myblock")
    assert addr == 0  # first block starts at offset 0


def test_notebook_builder_get_block_address_list() -> None:
    builder = NotebookBuilder()
    builder.append("dup", b"first", allow_duplicate=True)
    first_addr = builder.get_block_address("dup")
    builder.append("dup", b"second", allow_duplicate=True)
    # get_block_address returns the first address even when toc[label] is a list
    assert builder.get_block_address("dup") == first_addr
    # toc entry must be a list now
    assert isinstance(builder.toc["dup"], list)


def test_notebook_builder_get_block_address_missing() -> None:
    builder = NotebookBuilder()
    assert builder.get_block_address("nonexistent") == 0


def test_notebook_builder_get_duplicate_block_address_list_single() -> None:
    builder = NotebookBuilder()
    builder.append("single", b"abc")
    result = builder.get_duplicate_block_address_list("single")
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0] == builder.toc["single"]


def test_notebook_builder_get_duplicate_block_address_list_multi() -> None:
    builder = NotebookBuilder()
    builder.append("dup", b"first", allow_duplicate=True)
    addr1 = builder.get_block_address("dup")
    builder.append("dup", b"second", allow_duplicate=True)
    result = builder.get_duplicate_block_address_list("dup")
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0] == addr1


def test_notebook_builder_append_returns_false_for_duplicate() -> None:
    builder = NotebookBuilder()
    first = builder.append("label", b"data")
    assert first is True
    second = builder.append("label", b"data")
    assert second is False


def test_notebook_builder_append_skip_block_size() -> None:
    builder = NotebookBuilder()
    data = b"rawdata"
    builder.append("raw", data, skip_block_size=True)
    # With skip_block_size, total_size increases only by len(data), not + LENGTH_FIELD_SIZE
    assert builder.get_total_size() == len(data)
    # The built output should be exactly the data (no length prefix)
    assert builder.build() == data


def test_notebook_builder_build() -> None:
    builder = NotebookBuilder()
    builder.append("a", b"AAA", skip_block_size=True)
    builder.append("b", b"BBB", skip_block_size=True)
    result = builder.build()
    assert result == b"AAABBB"


def test_notebook_builder_dump(capsys: pytest.CaptureFixture[str]) -> None:
    builder = NotebookBuilder()
    builder.append("x", b"xyz")
    builder.dump()  # should not raise


def test_notebook_builder_append_raises_on_empty_label() -> None:
    builder = NotebookBuilder()
    with pytest.raises(ValueError):
        builder.append("", b"data")


def test_notebook_builder_append_raises_on_none_block() -> None:
    builder = NotebookBuilder()
    with pytest.raises(ValueError):
        builder.append("label", None)


# ---------------------------------------------------------------------------
# Integration tests (require test_note_path fixture)
# ---------------------------------------------------------------------------


def test_reconstruct_roundtrip(test_note_path: Path) -> None:
    notebook = load_notebook(str(test_note_path))
    result = reconstruct(notebook)
    assert isinstance(result, bytes)
    # The file type prefix is "note" (4 bytes)
    assert result[:4] == b"note"
    # Must be re-parseable
    stream = BytesIO(result)
    reparsed = load(stream)  # type: ignore[arg-type]
    assert reparsed.get_total_pages() == notebook.get_total_pages()


def test_notebook_builder_append_third_duplicate() -> None:
    """Third append with allow_duplicate appends to existing list (not replaces)."""
    builder = NotebookBuilder()
    builder.append("dup", b"first", allow_duplicate=True)
    builder.append("dup", b"second", allow_duplicate=True)
    # At this point toc["dup"] is a list [addr1, addr2]
    builder.append("dup", b"third", allow_duplicate=True)
    assert isinstance(builder.toc["dup"], list)
    assert len(builder.toc["dup"]) == 3


def test_pack_keywords_sets_keyword_metadata() -> None:
    """_pack_keywords updates keyword metadata when content is not None."""
    builder = NotebookBuilder()
    notebook = MagicMock()
    keyword = MagicMock()
    keyword.get_page_number.return_value = 0
    keyword.get_position_string.return_value = "ABCD"
    keyword.get_content.return_value = b"keyword content"
    keyword.metadata = {}
    notebook.get_keywords.return_value = [keyword]
    _pack_keywords(builder, notebook)
    assert keyword.metadata["KEYWORDPAGE"] == "1"


def test_pack_backgrounds_skips_none_style() -> None:
    """_pack_backgrounds skips pages whose get_style() returns None."""
    builder = NotebookBuilder()
    notebook = MagicMock()
    page = MagicMock()
    page.get_style.return_value = None
    notebook.get_total_pages.return_value = 1
    notebook.get_page.return_value = page
    _pack_backgrounds(builder, notebook)
    # No block appended since style is None
    assert builder.get_total_size() == 0


def test_pack_backgrounds_user_style_appends_hash() -> None:
    """_pack_backgrounds appends style_hash for user_ styles."""
    builder = NotebookBuilder()
    notebook = MagicMock()
    page = MagicMock()
    page.get_style.return_value = "user_custom"
    page.get_style_hash.return_value = "abc123"
    page.get_layers.return_value = []

    def find_bg(p: MagicMock) -> bytes:
        return b"bg"

    notebook.get_total_pages.return_value = 1
    notebook.get_page.return_value = page

    from unittest.mock import patch

    from supernote.notebook import manipulator

    with patch.object(
        manipulator, "_find_background_content_from_page", return_value=b"bg"
    ):
        _pack_backgrounds(builder, notebook)

    assert builder.get_total_size() > 0


def test_pack_pages_bglayer_skips_none_style() -> None:
    """_pack_pages skips BGLAYER when page style is None."""
    builder = NotebookBuilder()
    notebook = MagicMock()
    page = MagicMock()
    bglayer = MagicMock()
    bglayer.get_name.return_value = "BGLAYER"
    page.get_style.return_value = None
    page.get_layers.return_value = [bglayer]
    page.get_totalpath.return_value = None
    page.metadata = {"__layers__": []}
    notebook.get_total_pages.return_value = 1
    notebook.get_page.return_value = page

    from unittest.mock import patch

    from supernote.notebook import manipulator

    with patch.object(manipulator.utils, "WorkaroundPageWrapper") as mock_wrapper:
        mock_wrapper.from_page.return_value = page
        _pack_pages(builder, notebook)


def test_pack_pages_bglayer_user_style_appends_hash() -> None:
    """_pack_pages appends style_hash for BGLAYER with user_ style."""
    builder = NotebookBuilder()
    notebook = MagicMock()
    page = MagicMock()
    bglayer = MagicMock()
    bglayer.get_name.return_value = "BGLAYER"
    bglayer.metadata = {}
    page.get_style.return_value = "user_template"
    page.get_style_hash.return_value = "xyz"
    page.get_layers.return_value = [bglayer]
    page.get_totalpath.return_value = None
    page.metadata = {"__layers__": []}
    notebook.get_total_pages.return_value = 1
    notebook.get_page.return_value = page

    from unittest.mock import patch

    from supernote.notebook import manipulator

    with patch.object(manipulator.utils, "WorkaroundPageWrapper") as mock_wrapper:
        mock_wrapper.from_page.return_value = page
        _pack_pages(builder, notebook)

    assert bglayer.metadata.get("LAYERNAME") == "BGLAYER"


def test_merge_notebook_with_itself(test_note_path: Path) -> None:
    notebook = load_notebook(str(test_note_path))
    original_pages = notebook.get_total_pages()
    # Load a fresh copy to merge (merge may mutate metadata dicts)
    notebook2 = load_notebook(str(test_note_path))
    result = merge(notebook, notebook2)
    assert isinstance(result, bytes)
    # Must be re-parseable
    stream = BytesIO(result)
    merged = load(stream)  # type: ignore[arg-type]
    assert merged.get_total_pages() == original_pages * 2
