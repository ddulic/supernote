"""Prompt configuration API data models."""

from dataclasses import dataclass, field

from mashumaro import field_options
from mashumaro.config import BaseConfig
from mashumaro.mixins.json import DataClassJSONMixin

from .base import BaseResponse


@dataclass
class PromptConfigDTO(DataClassJSONMixin):
    """A single prompt layer configuration item."""

    category: str
    """Prompt category: 'ocr' or 'summary'."""

    layer: str
    """Prompt layer: 'common', 'default', or a custom type name."""

    content: str
    """Effective prompt text (user override if present, else server default)."""

    is_override: bool = field(metadata=field_options(alias="isOverride"), default=False)
    """True if a user-saved row exists for this (category, layer)."""

    default_content: str = field(
        metadata=field_options(alias="defaultContent"), default=""
    )
    """Server-file default text (always present for Reset support)."""

    class Config(BaseConfig):
        serialize_by_alias = True
        omit_none = True


@dataclass
class UpsertPromptConfigDTO(DataClassJSONMixin):
    """Request body for save/update of a single prompt layer."""

    category: str
    layer: str
    content: str

    class Config(BaseConfig):
        serialize_by_alias = True
        omit_none = True


@dataclass
class GetPromptsResponseVO(BaseResponse):
    """Response for GET /api/extended/prompts."""

    prompts: list[PromptConfigDTO] = field(default_factory=list)

    class Config(BaseConfig):
        serialize_by_alias = True
        omit_none = True


@dataclass
class PageStalenessDTO(DataClassJSONMixin):
    """Per-page staleness status."""

    page_id: str = field(metadata=field_options(alias="pageId"))
    page_index: int = field(metadata=field_options(alias="pageIndex"))
    stored_hash: str | None = field(
        metadata=field_options(alias="storedHash"), default=None
    )
    is_stale: bool = field(metadata=field_options(alias="isStale"), default=False)

    class Config(BaseConfig):
        serialize_by_alias = True
        omit_none = True


@dataclass
class FileStalenessResponseVO(BaseResponse):
    """Response for GET /api/extended/files/{id}/staleness."""

    current_prompt_hash: str = field(
        metadata=field_options(alias="currentPromptHash"), default=""
    )
    pages: list[PageStalenessDTO] = field(default_factory=list)
    stale_count: int = field(metadata=field_options(alias="staleCount"), default=0)
    total_count: int = field(metadata=field_options(alias="totalCount"), default=0)

    class Config(BaseConfig):
        serialize_by_alias = True
        omit_none = True


@dataclass
class ReprocessRequestDTO(DataClassJSONMixin):
    """Optional request body for POST /api/extended/files/{id}/reprocess."""

    page_ids: list[str] | None = field(
        metadata=field_options(alias="pageIds"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True
        omit_none = True


@dataclass
class ReprocessResponseVO(BaseResponse):
    """Response for reprocess endpoints."""

    queued_page_count: int = field(
        metadata=field_options(alias="queuedPageCount"), default=0
    )

    class Config(BaseConfig):
        serialize_by_alias = True
        omit_none = True
