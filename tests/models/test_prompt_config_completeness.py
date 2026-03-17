"""Tests for PromptConfig data models — round-trip serialisation."""

from supernote.models.prompt_config import (
    FileStalenessResponseVO,
    GetPromptsResponseVO,
    PageStalenessDTO,
    PromptConfigDTO,
    ReprocessRequestDTO,
    ReprocessResponseVO,
    UpsertPromptConfigDTO,
)


def test_prompt_config_dto_override() -> None:
    dto = PromptConfigDTO(
        category="ocr",
        layer="common",
        content="Do OCR.",
        is_override=True,
        default_content="Default OCR.",
    )
    d = dto.to_dict()
    assert d["category"] == "ocr"
    assert d["layer"] == "common"
    assert d["content"] == "Do OCR."
    assert d["isOverride"] is True
    assert d["defaultContent"] == "Default OCR."


def test_prompt_config_dto_no_override() -> None:
    dto = PromptConfigDTO(
        category="summary",
        layer="default",
        content="Summarise.",
        is_override=False,
        default_content="Summarise.",
    )
    d = dto.to_dict()
    assert d["isOverride"] is False
    assert d["defaultContent"] == "Summarise."


def test_upsert_prompt_config_dto() -> None:
    dto = UpsertPromptConfigDTO(
        category="summary",
        layer="monthly",
        content="Monthly summary prompt.",
    )
    d = dto.to_dict()
    assert d["category"] == "summary"
    assert d["layer"] == "monthly"
    assert d["content"] == "Monthly summary prompt."


def test_get_prompts_response_vo() -> None:
    prompts = [
        PromptConfigDTO(
            category="ocr",
            layer="default",
            content="OCR default.",
            is_override=False,
            default_content="OCR default.",
        )
    ]
    vo = GetPromptsResponseVO(success=True, prompts=prompts)
    d = vo.to_dict()
    assert d["success"] is True
    assert len(d["prompts"]) == 1
    assert d["prompts"][0]["category"] == "ocr"


def test_get_prompts_response_vo_empty() -> None:
    vo = GetPromptsResponseVO(success=True)
    d = vo.to_dict()
    assert d["prompts"] == []


def test_page_staleness_dto_stale() -> None:
    dto = PageStalenessDTO(
        page_id="P20231027120000abc",
        page_index=0,
        stored_hash=None,
        is_stale=True,
    )
    d = dto.to_dict()
    assert d["pageId"] == "P20231027120000abc"
    assert d["pageIndex"] == 0
    assert d["isStale"] is True
    assert "storedHash" not in d  # omit_none


def test_page_staleness_dto_not_stale() -> None:
    dto = PageStalenessDTO(
        page_id="P20231028090000xyz",
        page_index=1,
        stored_hash="a3f1e9c2",
        is_stale=False,
    )
    d = dto.to_dict()
    assert d["storedHash"] == "a3f1e9c2"
    assert d["isStale"] is False


def test_file_staleness_response_vo() -> None:
    pages = [
        PageStalenessDTO(page_id="P1", page_index=0, stored_hash=None, is_stale=True),
        PageStalenessDTO(
            page_id="P2", page_index=1, stored_hash="abc123", is_stale=False
        ),
    ]
    vo = FileStalenessResponseVO(
        success=True,
        current_prompt_hash="def456",
        pages=pages,
        stale_count=1,
        total_count=2,
    )
    d = vo.to_dict()
    assert d["success"] is True
    assert d["currentPromptHash"] == "def456"
    assert d["staleCount"] == 1
    assert d["totalCount"] == 2
    assert len(d["pages"]) == 2


def test_reprocess_request_dto_with_page_ids() -> None:
    dto = ReprocessRequestDTO(page_ids=["P1", "P2"])
    d = dto.to_dict()
    assert d["pageIds"] == ["P1", "P2"]


def test_reprocess_request_dto_none() -> None:
    dto = ReprocessRequestDTO()
    d = dto.to_dict()
    assert "pageIds" not in d  # omit_none


def test_reprocess_response_vo() -> None:
    vo = ReprocessResponseVO(success=True, queued_page_count=3)
    d = vo.to_dict()
    assert d["success"] is True
    assert d["queuedPageCount"] == 3
