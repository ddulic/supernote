import pytest

from supernote.server.utils.prompt_loader import (
    DEFAULT_OCR_PROMPT,
    DEFAULT_SUMMARY_COMMON_PROMPT,
    DEFAULT_SUMMARY_PROMPT,
    PromptId,
    PromptLoader,
)


@pytest.fixture
def loader() -> PromptLoader:
    return PromptLoader()


def test_get_prompt_ocr_returns_default(loader: PromptLoader) -> None:
    assert loader.get_prompt(PromptId.OCR_TRANSCRIPTION) == DEFAULT_OCR_PROMPT


def test_get_prompt_summary_composes_common_and_default(loader: PromptLoader) -> None:
    """Summary prompt is common + default joined."""
    prompt = loader.get_prompt(PromptId.SUMMARY_GENERATION)
    assert DEFAULT_SUMMARY_COMMON_PROMPT in prompt
    assert DEFAULT_SUMMARY_PROMPT in prompt


def test_get_prompt_custom_type_ignored(loader: PromptLoader) -> None:
    """custom_type is ignored — loader always returns the hardcoded default."""
    assert (
        loader.get_prompt(PromptId.OCR_TRANSCRIPTION, custom_type="daily")
        == DEFAULT_OCR_PROMPT
    )


def test_get_prompt_unknown_id_raises(loader: PromptLoader) -> None:
    with pytest.raises(ValueError):
        loader.get_prompt("nonexistent")  # type: ignore[arg-type]


def test_get_all_known_layers_ocr(loader: PromptLoader) -> None:
    layers = loader.get_all_known_layers()
    assert layers["ocr_transcription"]["default"] == DEFAULT_OCR_PROMPT
    assert "common" not in layers["ocr_transcription"]


def test_get_all_known_layers_summary(loader: PromptLoader) -> None:
    layers = loader.get_all_known_layers()
    assert layers["summary_generation"]["common"] == DEFAULT_SUMMARY_COMMON_PROMPT
    assert layers["summary_generation"]["default"] == DEFAULT_SUMMARY_PROMPT


def test_default_prompts_are_nonempty() -> None:
    assert DEFAULT_OCR_PROMPT.strip()
    assert DEFAULT_SUMMARY_COMMON_PROMPT.strip()
    assert DEFAULT_SUMMARY_PROMPT.strip()
