"""Tests for supernote.notebook.fileformat module."""

import json
from pathlib import Path

from supernote.notebook.fileformat import (
    Cover,
    Page,
    SupernoteMetadata,
)
from supernote.notebook.parser import load_notebook

# ---------------------------------------------------------------------------
# Notebook integration tests (require test_note_path fixture)
# ---------------------------------------------------------------------------


def test_notebook_get_width_height(test_note_path: Path) -> None:
    notebook = load_notebook(str(test_note_path))
    assert isinstance(notebook.get_width(), int)
    assert isinstance(notebook.get_height(), int)
    assert notebook.get_width() > 0
    assert notebook.get_height() > 0


def test_notebook_get_type(test_note_path: Path) -> None:
    notebook = load_notebook(str(test_note_path))
    assert notebook.get_type() is not None
    assert notebook.get_type().upper() == "NOTE"  # type: ignore[union-attr]  # checked above


def test_notebook_get_signature(test_note_path: Path) -> None:
    notebook = load_notebook(str(test_note_path))
    assert notebook.get_signature() == "SN_FILE_VER_20230015"


def test_notebook_get_total_pages(test_note_path: Path) -> None:
    notebook = load_notebook(str(test_note_path))
    assert notebook.get_total_pages() >= 1


def test_notebook_get_fileid(test_note_path: Path) -> None:
    notebook = load_notebook(str(test_note_path))
    fileid = notebook.get_fileid()
    assert fileid is not None
    assert len(fileid) > 0


def test_notebook_get_page(test_note_path: Path) -> None:
    notebook = load_notebook(str(test_note_path))
    page = notebook.get_page(0)
    assert isinstance(page, Page)


def test_notebook_get_cover(test_note_path: Path) -> None:
    notebook = load_notebook(str(test_note_path))
    cover = notebook.get_cover()
    assert isinstance(cover, Cover)


def test_notebook_get_keywords(test_note_path: Path) -> None:
    notebook = load_notebook(str(test_note_path))
    keywords = notebook.get_keywords()
    assert isinstance(keywords, list)


def test_notebook_get_titles(test_note_path: Path) -> None:
    notebook = load_notebook(str(test_note_path))
    titles = notebook.get_titles()
    assert isinstance(titles, list)


def test_notebook_get_links(test_note_path: Path) -> None:
    notebook = load_notebook(str(test_note_path))
    links = notebook.get_links()
    assert isinstance(links, list)


def test_notebook_is_realtime_recognition(test_note_path: Path) -> None:
    notebook = load_notebook(str(test_note_path))
    result = notebook.is_realtime_recognition()
    assert isinstance(result, bool)


def test_notebook_supports_highres_grayscale(test_note_path: Path) -> None:
    notebook = load_notebook(str(test_note_path))
    result = notebook.supports_highres_grayscale()
    assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# SupernoteMetadata unit tests
# ---------------------------------------------------------------------------


def _make_minimal_metadata() -> SupernoteMetadata:
    """Create a minimal valid SupernoteMetadata for unit testing."""
    meta = SupernoteMetadata()
    meta.type = "NOTE"
    meta.signature = "SN_FILE_VER_20230015"
    meta.header = {"FILE_TYPE": "NOTE", "APPLY_EQUIPMENT": "N6"}
    meta.footer = {}
    meta.pages = [{}]
    return meta


def test_supernote_metadata_properties() -> None:
    meta = SupernoteMetadata()
    meta.type = "NOTE"
    meta.signature = "SN_FILE_VER_20230015"
    meta.header = {"FILE_TYPE": "NOTE"}
    meta.footer = {"FILE_FEATURE": "100"}
    meta.pages = [{}]

    assert meta.type == "NOTE"
    assert meta.signature == "SN_FILE_VER_20230015"
    assert meta.header == {"FILE_TYPE": "NOTE"}
    assert meta.footer == {"FILE_FEATURE": "100"}
    assert meta.pages == [{}]


def test_supernote_metadata_get_total_pages_empty() -> None:
    meta = SupernoteMetadata()
    assert meta.get_total_pages() == 0


def test_supernote_metadata_is_layer_supported(test_note_path: Path) -> None:
    notebook = load_notebook(str(test_note_path))
    meta = notebook.get_metadata()
    result = meta.is_layer_supported(0)
    assert isinstance(result, bool)


def test_supernote_metadata_to_json() -> None:
    meta = _make_minimal_metadata()
    json_str = meta.to_json()
    assert isinstance(json_str, str)
    # Must be valid JSON
    parsed = json.loads(json_str)
    assert isinstance(parsed, dict)


# ---------------------------------------------------------------------------
# Cover tests
# ---------------------------------------------------------------------------


def test_cover_content(test_note_path: Path) -> None:
    notebook = load_notebook(str(test_note_path))
    cover = notebook.get_cover()
    cover.set_content(b"test")
    assert cover.get_content() == b"test"


# ---------------------------------------------------------------------------
# Page tests
# ---------------------------------------------------------------------------


def test_page_get_layers(test_note_path: Path) -> None:
    notebook = load_notebook(str(test_note_path))
    page = notebook.get_page(0)
    layers = page.get_layers()
    assert isinstance(layers, list)


def test_page_get_protocol(test_note_path: Path) -> None:
    notebook = load_notebook(str(test_note_path))
    page = notebook.get_page(0)
    protocol = page.get_protocol()
    assert protocol is None or isinstance(protocol, str)


def test_page_get_style(test_note_path: Path) -> None:
    notebook = load_notebook(str(test_note_path))
    page = notebook.get_page(0)
    style = page.get_style()
    assert style is None or isinstance(style, str)


def test_page_get_orientation(test_note_path: Path) -> None:
    notebook = load_notebook(str(test_note_path))
    page = notebook.get_page(0)
    orientation = page.get_orientation()
    assert isinstance(orientation, str)


def test_page_get_pageid(test_note_path: Path) -> None:
    notebook = load_notebook(str(test_note_path))
    page = notebook.get_page(0)
    pageid = page.get_pageid()
    assert pageid is None or isinstance(pageid, str)


def test_page_get_recogn_status(test_note_path: Path) -> None:
    notebook = load_notebook(str(test_note_path))
    page = notebook.get_page(0)
    status = page.get_recogn_status()
    assert isinstance(status, int)


def test_page_set_get_recogn_file(test_note_path: Path) -> None:
    notebook = load_notebook(str(test_note_path))
    page = notebook.get_page(0)
    page.set_recogn_file(b"data")
    assert page.get_recogn_file() == b"data"


def test_page_set_get_recogn_text(test_note_path: Path) -> None:
    notebook = load_notebook(str(test_note_path))
    page = notebook.get_page(0)
    page.set_recogn_text(b"text")
    assert page.get_recogn_text() == b"text"


def test_page_set_get_totalpath(test_note_path: Path) -> None:
    notebook = load_notebook(str(test_note_path))
    page = notebook.get_page(0)
    page.set_totalpath(b"path")
    assert page.get_totalpath() == b"path"


def test_page_get_layer_order(test_note_path: Path) -> None:
    notebook = load_notebook(str(test_note_path))
    page = notebook.get_page(0)
    order = page.get_layer_order()
    assert isinstance(order, list)
