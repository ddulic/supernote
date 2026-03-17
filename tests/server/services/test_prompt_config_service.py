"""Tests for PromptConfigService — CRUD, prompt resolution, hash computation."""

import pytest

from supernote.server.db.session import DatabaseSessionManager
from supernote.server.services.prompt_config import NotFoundError, PromptConfigService
from supernote.server.utils.prompt_loader import (
    DEFAULT_OCR_PROMPT,
    DEFAULT_SUMMARY_COMMON_PROMPT,
    DEFAULT_SUMMARY_PROMPT,
    PromptId,
    PromptLoader,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def prompt_loader() -> PromptLoader:
    return PromptLoader()


@pytest.fixture
def service(
    session_manager: DatabaseSessionManager, prompt_loader: PromptLoader
) -> PromptConfigService:
    """Create a PromptConfigService with in-process DB."""
    return PromptConfigService(session_manager, prompt_loader)


# ---------------------------------------------------------------------------
# list_configs
# ---------------------------------------------------------------------------


async def test_list_configs_empty(service: PromptConfigService) -> None:
    """New user has no configs."""
    configs = await service.list_configs(user_id=1)
    assert configs == []


async def test_list_configs_after_upsert(service: PromptConfigService) -> None:
    """Configs appear after upsert."""
    await service.upsert_config(
        user_id=1, category="ocr", layer="common", content="My OCR"
    )
    configs = await service.list_configs(user_id=1)
    assert len(configs) == 1
    assert configs[0].category == "ocr"
    assert configs[0].layer == "common"
    assert configs[0].content == "My OCR"


async def test_list_configs_user_isolation(service: PromptConfigService) -> None:
    """Each user sees only their own configs."""
    await service.upsert_config(
        user_id=1, category="ocr", layer="default", content="User1 OCR"
    )
    await service.upsert_config(
        user_id=2, category="ocr", layer="default", content="User2 OCR"
    )
    user1_configs = await service.list_configs(user_id=1)
    user2_configs = await service.list_configs(user_id=2)
    assert len(user1_configs) == 1
    assert len(user2_configs) == 1
    assert user1_configs[0].content == "User1 OCR"
    assert user2_configs[0].content == "User2 OCR"


# ---------------------------------------------------------------------------
# upsert_config
# ---------------------------------------------------------------------------


async def test_upsert_config_creates_row(service: PromptConfigService) -> None:
    """Upsert creates a new row when none exists."""
    row = await service.upsert_config(
        user_id=1, category="summary", layer="monthly", content="Monthly prompt"
    )
    assert row.user_id == 1
    assert row.category == "summary"
    assert row.layer == "monthly"
    assert row.content == "Monthly prompt"


async def test_upsert_config_updates_row(service: PromptConfigService) -> None:
    """Upsert updates the row when one exists."""
    await service.upsert_config(
        user_id=1, category="ocr", layer="common", content="First"
    )
    updated = await service.upsert_config(
        user_id=1, category="ocr", layer="common", content="Second"
    )
    assert updated.content == "Second"
    all_configs = await service.list_configs(user_id=1)
    assert len(all_configs) == 1


async def test_upsert_config_invalid_category(service: PromptConfigService) -> None:
    """Upsert raises ValueError for unknown category."""
    with pytest.raises(ValueError, match="category"):
        await service.upsert_config(
            user_id=1, category="invalid", layer="default", content="Some text"
        )


async def test_upsert_config_empty_content(service: PromptConfigService) -> None:
    """Upsert raises ValueError for empty/whitespace content."""
    with pytest.raises(ValueError, match="content"):
        await service.upsert_config(
            user_id=1, category="ocr", layer="default", content="   "
        )


async def test_upsert_config_invalid_layer(service: PromptConfigService) -> None:
    """Upsert raises ValueError for invalid layer name."""
    with pytest.raises(ValueError, match="layer"):
        await service.upsert_config(
            user_id=1, category="ocr", layer="invalid layer!", content="Some text"
        )


# ---------------------------------------------------------------------------
# delete_config
# ---------------------------------------------------------------------------


async def test_delete_config_existing(service: PromptConfigService) -> None:
    """Delete removes the row."""
    await service.upsert_config(
        user_id=1, category="ocr", layer="monthly", content="Monthly OCR"
    )
    await service.delete_config(user_id=1, category="ocr", layer="monthly")
    configs = await service.list_configs(user_id=1)
    assert configs == []


async def test_delete_config_not_found(service: PromptConfigService) -> None:
    """Delete raises NotFoundError when no DB row exists for that layer."""
    with pytest.raises(NotFoundError):
        await service.delete_config(user_id=1, category="ocr", layer="nonexistent")


async def test_delete_config_protected_layer_raises(
    service: PromptConfigService,
) -> None:
    """Protected layers cannot be deleted even when a user override exists."""
    await service.upsert_config(
        user_id=1, category="ocr", layer="default", content="custom"
    )
    with pytest.raises(ValueError, match="protected"):
        await service.delete_config(user_id=1, category="ocr", layer="default")

    with pytest.raises(ValueError, match="protected"):
        await service.delete_config(user_id=1, category="summary", layer="common")


async def test_delete_config_user_isolation(service: PromptConfigService) -> None:
    """Delete only removes the specified user's config."""
    await service.upsert_config(
        user_id=1, category="ocr", layer="project", content="User1"
    )
    await service.upsert_config(
        user_id=2, category="ocr", layer="project", content="User2"
    )
    await service.delete_config(user_id=1, category="ocr", layer="project")
    assert await service.list_configs(user_id=1) == []
    assert len(await service.list_configs(user_id=2)) == 1


# ---------------------------------------------------------------------------
# get_effective_prompt
# ---------------------------------------------------------------------------


async def test_get_effective_prompt_ocr_falls_back_to_loader(
    service: PromptConfigService,
) -> None:
    """With no user override, OCR returns the hardcoded default."""
    prompt = await service.get_effective_prompt(
        user_id=1, prompt_id=PromptId.OCR_TRANSCRIPTION, note_type=None
    )
    assert prompt == DEFAULT_OCR_PROMPT


async def test_get_effective_prompt_summary_composes_common_and_default(
    service: PromptConfigService,
) -> None:
    """With no user overrides, summary composes common + default."""
    prompt = await service.get_effective_prompt(
        user_id=1, prompt_id=PromptId.SUMMARY_GENERATION, note_type=None
    )
    assert DEFAULT_SUMMARY_COMMON_PROMPT in prompt
    assert DEFAULT_SUMMARY_PROMPT in prompt


async def test_get_effective_prompt_uses_user_default_override(
    service: PromptConfigService,
) -> None:
    """User override for 'default' replaces the hardcoded default."""
    await service.upsert_config(
        user_id=1, category="ocr", layer="default", content="My custom OCR"
    )
    prompt = await service.get_effective_prompt(
        user_id=1, prompt_id=PromptId.OCR_TRANSCRIPTION, note_type=None
    )
    assert prompt == "My custom OCR"


async def test_get_effective_prompt_note_type_override_wins(
    service: PromptConfigService,
) -> None:
    """User override for a specific note type takes priority over 'default'."""
    await service.upsert_config(
        user_id=1, category="ocr", layer="default", content="My default OCR"
    )
    await service.upsert_config(
        user_id=1, category="ocr", layer="monthly", content="My monthly OCR"
    )
    prompt = await service.get_effective_prompt(
        user_id=1, prompt_id=PromptId.OCR_TRANSCRIPTION, note_type="monthly"
    )
    assert prompt == "My monthly OCR"


async def test_get_effective_prompt_note_type_falls_back_to_default_override(
    service: PromptConfigService,
) -> None:
    """When no type-specific override exists, uses the 'default' override."""
    await service.upsert_config(
        user_id=1, category="ocr", layer="default", content="My default OCR"
    )
    prompt = await service.get_effective_prompt(
        user_id=1, prompt_id=PromptId.OCR_TRANSCRIPTION, note_type="weekly"
    )
    assert prompt == "My default OCR"


# ---------------------------------------------------------------------------
# compute_combined_prompt_hash
# ---------------------------------------------------------------------------


async def test_compute_combined_prompt_hash_returns_hex(
    service: PromptConfigService,
) -> None:
    """compute_combined_prompt_hash returns a 64-char hex string."""
    h = await service.compute_combined_prompt_hash(user_id=1, note_type=None)
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


async def test_compute_combined_prompt_hash_changes_on_override(
    service: PromptConfigService,
) -> None:
    """Hash changes when a user override is added."""
    h1 = await service.compute_combined_prompt_hash(user_id=1, note_type=None)
    await service.upsert_config(
        user_id=1, category="ocr", layer="default", content="Changed OCR"
    )
    h2 = await service.compute_combined_prompt_hash(user_id=1, note_type=None)
    assert h1 != h2


async def test_compute_combined_prompt_hash_user_isolation(
    service: PromptConfigService,
) -> None:
    """Hash is per-user; different user overrides produce different hashes."""
    h_baseline = await service.compute_combined_prompt_hash(user_id=1, note_type=None)
    await service.upsert_config(
        user_id=2, category="ocr", layer="default", content="User2 OCR"
    )
    h_user1 = await service.compute_combined_prompt_hash(user_id=1, note_type=None)
    h_user2 = await service.compute_combined_prompt_hash(user_id=2, note_type=None)
    assert h_user1 == h_baseline
    assert h_user2 != h_baseline


# ---------------------------------------------------------------------------
# get_all_configs_with_defaults
# ---------------------------------------------------------------------------


async def test_get_all_configs_with_defaults_includes_all_layers(
    service: PromptConfigService,
) -> None:
    """Returns both default layers from the loader (no user overrides)."""
    configs = await service.get_all_configs_with_defaults(user_id=1)
    categories = {c.category for c in configs}
    assert "ocr" in categories
    assert "summary" in categories
    layers = {c.layer for c in configs if c.category == "ocr"}
    assert "default" in layers


async def test_get_all_configs_with_defaults_marks_overrides(
    service: PromptConfigService,
) -> None:
    """is_override is True only for layers with user DB rows."""
    await service.upsert_config(
        user_id=1, category="ocr", layer="default", content="My custom OCR"
    )
    configs = await service.get_all_configs_with_defaults(user_id=1)
    override_configs = [c for c in configs if c.is_override]
    non_override_configs = [c for c in configs if not c.is_override]
    assert len(override_configs) == 1
    assert override_configs[0].category == "ocr"
    assert override_configs[0].layer == "default"
    assert override_configs[0].content == "My custom OCR"
    assert all(c.default_content for c in non_override_configs)


async def test_get_all_configs_with_defaults_default_content_always_present(
    service: PromptConfigService,
) -> None:
    """default_content always holds the hardcoded default text."""
    await service.upsert_config(
        user_id=1, category="ocr", layer="default", content="Override text"
    )
    configs = await service.get_all_configs_with_defaults(user_id=1)
    for c in configs:
        assert c.default_content, f"Missing default_content for {c.category}/{c.layer}"
