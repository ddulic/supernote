"""Tests for supernote.notebook.fileformat module."""

import json
from pathlib import Path

import pytest

from supernote.notebook.fileformat import (
    A5X2_PAGE_HEIGHT,
    A5X2_PAGE_WIDTH,
    Cover,
    Keyword,
    Layer,
    Link,
    Notebook,
    Page,
    SupernoteMetadata,
    Title,
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


# ---------------------------------------------------------------------------
# Notebook unit tests (without real file)
# ---------------------------------------------------------------------------


def _make_minimal_notebook() -> Notebook:
    """Create a minimal Notebook for unit testing."""
    meta = SupernoteMetadata()
    meta.type = "NOTE"
    meta.signature = "SN_FILE_VER_20230015"
    meta.header = {"FILE_TYPE": "NOTE", "APPLY_EQUIPMENT": "N6"}
    meta.footer = {}
    meta.pages = [{"RECOGNSTATUS": "0"}]
    return Notebook(meta)


def test_notebook_n5_uses_a5x2_dimensions() -> None:
    meta = SupernoteMetadata()
    meta.type = "NOTE"
    meta.signature = "SN_FILE_VER_20230015"
    meta.header = {"FILE_TYPE": "NOTE", "APPLY_EQUIPMENT": "N5"}
    meta.footer = {}
    meta.pages = [{"RECOGNSTATUS": "0"}]
    nb = Notebook(meta)
    assert nb.get_width() == A5X2_PAGE_WIDTH
    assert nb.get_height() == A5X2_PAGE_HEIGHT


def test_notebook_get_page_out_of_range() -> None:
    nb = _make_minimal_notebook()
    with pytest.raises(IndexError):
        nb.get_page(-1)
    with pytest.raises(IndexError):
        nb.get_page(100)


def test_notebook_with_keywords_in_footer() -> None:
    meta = SupernoteMetadata()
    meta.type = "NOTE"
    meta.signature = "SN_FILE_VER_20230015"
    meta.header = {"FILE_TYPE": "NOTE", "APPLY_EQUIPMENT": "N6"}
    meta.footer = {
        "__keywords__": [
            {  # type: ignore[list-item]  # forked binary format; nested dicts
                "KEYWORDPAGE": "1",
                "KEYWORDRECTORI": "10,20,100,50",
                "KEYWORD": "test",
                "KEYWORDRECT": "10,20,100,50",
            }
        ]
    }
    meta.pages = [{"RECOGNSTATUS": "0"}]
    nb = Notebook(meta)
    assert len(nb.get_keywords()) == 1


def test_notebook_with_titles_in_footer() -> None:
    meta = SupernoteMetadata()
    meta.type = "NOTE"
    meta.signature = "SN_FILE_VER_20230015"
    meta.header = {"FILE_TYPE": "NOTE", "APPLY_EQUIPMENT": "N6"}
    meta.footer = {"__titles__": [{"TITLERECTORI": "10,20,100,50"}]}  # type: ignore[list-item]  # forked binary format
    meta.pages = [{"RECOGNSTATUS": "0"}]
    nb = Notebook(meta)
    assert len(nb.get_titles()) == 1


def test_notebook_with_links_in_footer() -> None:
    meta = SupernoteMetadata()
    meta.type = "NOTE"
    meta.signature = "SN_FILE_VER_20230015"
    meta.header = {"FILE_TYPE": "NOTE", "APPLY_EQUIPMENT": "N6"}
    meta.footer = {
        "__links__": [
            {  # type: ignore[list-item]  # forked binary format; nested dicts
                "LINKTYPE": "4",
                "LINKINOUT": "0",
                "LINKRECT": "5,10,200,100",
                "LINKTIMESTAMP": "20230101120000",
                "LINKFILE": "aHR0cHM6Ly9leGFtcGxlLmNvbQ==",
                "LINKFILEID": "none",
                "PAGEID": "none",
            }
        ]
    }
    meta.pages = [{"RECOGNSTATUS": "0"}]
    nb = Notebook(meta)
    assert len(nb.get_links()) == 1


def test_supernote_metadata_is_layer_supported_out_of_range() -> None:
    meta = SupernoteMetadata()
    meta.pages = [{}]
    with pytest.raises(IndexError):
        meta.is_layer_supported(5)


# ---------------------------------------------------------------------------
# Keyword unit tests
# ---------------------------------------------------------------------------


def _make_keyword() -> Keyword:
    return Keyword(
        {
            "KEYWORDPAGE": "2",
            "KEYWORDRECTORI": "10,20,100,50",
            "KEYWORD": "hello",
            "KEYWORDRECT": "10,20,100,50",
        }
    )


def test_keyword_page_number() -> None:
    kw = _make_keyword()
    assert kw.get_page_number() == 1  # KEYWORDPAGE "2" → 0-indexed = 1


def test_keyword_set_get_content() -> None:
    kw = _make_keyword()
    kw.set_content(b"img")
    assert kw.get_content() == b"img"


def test_keyword_get_position_string() -> None:
    kw = _make_keyword()
    assert kw.get_position_string() == "0020"


def test_keyword_get_keyword() -> None:
    kw = _make_keyword()
    assert kw.get_keyword() == "hello"


def test_keyword_get_rect() -> None:
    kw = _make_keyword()
    assert kw.get_rect() == (10, 20, 110, 70)


# ---------------------------------------------------------------------------
# Title unit tests
# ---------------------------------------------------------------------------


def _make_title() -> Title:
    return Title({"TITLERECTORI": "10,20,100,50"})


def test_title_set_get_content() -> None:
    t = _make_title()
    t.set_content(b"bitmap")
    assert t.get_content() == b"bitmap"


def test_title_set_get_page_number() -> None:
    t = _make_title()
    t.set_page_number(3)
    assert t.get_page_number() == 3


def test_title_get_position_string() -> None:
    t = _make_title()
    assert t.get_position_string() == "00200010"


# ---------------------------------------------------------------------------
# Link unit tests
# ---------------------------------------------------------------------------


def _make_link() -> Link:
    return Link(
        {
            "LINKTYPE": "4",
            "LINKINOUT": "0",
            "LINKRECT": "5,10,200,100",
            "LINKTIMESTAMP": "20230101120000",
            "LINKFILE": "aHR0cHM6Ly9leGFtcGxlLmNvbQ==",
            "LINKFILEID": "none",
            "PAGEID": "none",
        }
    )


def test_link_set_get_content() -> None:
    link = _make_link()
    link.set_content(b"bitmap")
    assert link.get_content() == b"bitmap"


def test_link_set_get_page_number() -> None:
    link = _make_link()
    link.set_page_number(5)
    assert link.get_page_number() == 5


def test_link_get_type() -> None:
    assert _make_link().get_type() == 4


def test_link_get_inout() -> None:
    assert _make_link().get_inout() == 0


def test_link_get_timestamp() -> None:
    assert _make_link().get_timestamp() == "20230101120000"


def test_link_get_filepath() -> None:
    assert _make_link().get_filepath() == "aHR0cHM6Ly9leGFtcGxlLmNvbQ=="


def test_link_get_fileid_none() -> None:
    assert _make_link().get_fileid() is None


def test_link_get_pageid_none() -> None:
    assert _make_link().get_pageid() is None


def test_link_get_fileid_value() -> None:
    link = Link(
        {
            "LINKTYPE": "0",
            "LINKINOUT": "1",
            "LINKRECT": "0,0,10,10",
            "LINKTIMESTAMP": "20230101000000",
            "LINKFILE": "",
            "LINKFILEID": "abc123",
            "PAGEID": "page001",
        }
    )
    assert link.get_fileid() == "abc123"
    assert link.get_pageid() == "page001"


def test_link_get_rect() -> None:
    assert _make_link().get_rect() == (5, 10, 205, 110)


def test_link_get_position_string() -> None:
    pos = _make_link().get_position_string()
    assert isinstance(pos, str)
    assert len(pos) > 0


# ---------------------------------------------------------------------------
# Page unit tests (without real file)
# ---------------------------------------------------------------------------


def test_page_get_style_hash_zero_returns_empty_string() -> None:
    page = Page({"RECOGNSTATUS": "0", "PAGESTYLEMD5": "0"})
    assert page.get_style_hash() == ""


def test_page_get_style_hash_value() -> None:
    page = Page({"RECOGNSTATUS": "0", "PAGESTYLEMD5": "abc123"})
    assert page.get_style_hash() == "abc123"


def test_page_get_layer_info_missing_returns_none() -> None:
    page = Page({"RECOGNSTATUS": "0"})
    assert page.get_layer_info() is None


def test_page_get_layer_info_none_string_returns_none() -> None:
    page = Page({"RECOGNSTATUS": "0", "LAYERINFO": "none"})
    assert page.get_layer_info() is None


def test_page_get_layer_info_replaces_hash() -> None:
    page = Page({"RECOGNSTATUS": "0", "LAYERINFO": "key#value#extra"})
    assert page.get_layer_info() == "key:value:extra"


def test_page_get_layer_order_with_data() -> None:
    page = Page({"RECOGNSTATUS": "0", "LAYERSEQ": "LAYER1,LAYER2,MAINLAYER"})
    assert page.get_layer_order() == ["LAYER1", "LAYER2", "MAINLAYER"]


def test_page_get_layer_out_of_range() -> None:
    page = Page({"RECOGNSTATUS": "0"})
    with pytest.raises(IndexError):
        page.get_layer(-1)


def test_page_get_protocol_no_layer() -> None:
    page = Page({"RECOGNSTATUS": "0", "PROTOCOL": "RATTA_RLE"})
    assert page.get_protocol() == "RATTA_RLE"


# ---------------------------------------------------------------------------
# Layer unit tests
# ---------------------------------------------------------------------------


def test_layer_get_protocol() -> None:
    layer = Layer({"LAYERNAME": "MAINLAYER", "LAYERPROTOCOL": "RATTA_RLE"})
    assert layer.get_protocol() == "RATTA_RLE"


def test_layer_get_type() -> None:
    layer = Layer({"LAYERNAME": "MAINLAYER", "LAYERTYPE": "TEXT"})
    assert layer.get_type() == "TEXT"


def test_layer_set_get_content() -> None:
    layer = Layer({"LAYERNAME": "MAINLAYER"})
    layer.set_content(b"raw")
    assert layer.get_content() == b"raw"
