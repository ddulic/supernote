"""Round-trip serialisation tests for OCR-related models in supernote.models.extended.

Per constitution §VI: written before implementation; must FAIL until DTOs/VOs are added.
"""

from supernote.models.extended import (
    OcrPageVO,
    WebOcrListRequestDTO,
    WebOcrListVO,
)


def test_ocr_page_vo_round_trip() -> None:
    vo = OcrPageVO(page_index=0, text_content="Hello world")
    d = vo.to_dict()
    assert d["pageIndex"] == 0
    assert d["textContent"] == "Hello world"


def test_ocr_page_vo_alias_serialisation() -> None:
    """Verify camelCase aliases are used in JSON output."""
    vo = OcrPageVO(page_index=3, text_content="Page text")
    d = vo.to_dict()
    assert "pageIndex" in d
    assert "textContent" in d
    assert "page_index" not in d
    assert "text_content" not in d


def test_web_ocr_list_request_dto_round_trip() -> None:
    dto = WebOcrListRequestDTO(file_id=42)
    d = dto.to_dict()
    assert d["fileId"] == 42
    assert "file_id" not in d


def test_web_ocr_list_request_dto_from_dict() -> None:
    dto = WebOcrListRequestDTO.from_dict({"fileId": 99})
    assert dto.file_id == 99


def test_web_ocr_list_vo_empty_pages() -> None:
    vo = WebOcrListVO(pages=[])
    d = vo.to_dict()
    assert d["pages"] == []


def test_web_ocr_list_vo_with_pages() -> None:
    pages = [
        OcrPageVO(page_index=0, text_content="First page"),
        OcrPageVO(page_index=1, text_content="Second page"),
    ]
    vo = WebOcrListVO(pages=pages)
    d = vo.to_dict()
    assert len(d["pages"]) == 2
    assert d["pages"][0]["pageIndex"] == 0
    assert d["pages"][0]["textContent"] == "First page"
    assert d["pages"][1]["pageIndex"] == 1


def test_web_ocr_list_vo_pages_order_preserved() -> None:
    pages = [OcrPageVO(page_index=i, text_content=f"p{i}") for i in range(5)]
    vo = WebOcrListVO(pages=pages)
    d = vo.to_dict()
    indices = [p["pageIndex"] for p in d["pages"]]
    assert indices == list(range(5))
