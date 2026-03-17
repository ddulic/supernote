"""PromptConfigService — per-user prompt configuration management."""

import hashlib
import logging
import re
from typing import Callable

from sqlalchemy import delete, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from supernote.models.prompt_config import PromptConfigDTO
from supernote.server.db.models.prompt_config import PromptConfigDO
from supernote.server.db.session import DatabaseSessionManager
from supernote.server.utils.prompt_loader import (
    CATEGORY_MAP,
    COMMON,
    DEFAULT,
    PROTECTED_LAYERS,
    PromptId,
    PromptLoader,
)

logger = logging.getLogger(__name__)

VALID_CATEGORIES = {"ocr", "summary"}
_LAYER_RE = re.compile(r"^[a-zA-Z0-9-]{1,64}$")

# Map prompt_id value → category string (reverse of CATEGORY_MAP)
_PROMPT_ID_TO_CATEGORY: dict[str, str] = {v: k for k, v in CATEGORY_MAP.items()}
# Map category string → PromptId enum
_CATEGORY_TO_PROMPT_ID: dict[str, PromptId] = {
    k: PromptId(v) for k, v in CATEGORY_MAP.items()
}


class NotFoundError(Exception):
    """Raised when a requested resource does not exist."""


class PromptConfigService:
    """Service for managing per-user prompt configuration overrides."""

    def __init__(
        self,
        session_manager: DatabaseSessionManager,
        prompt_loader: PromptLoader,
    ) -> None:
        self._session_manager = session_manager
        self._prompt_loader = prompt_loader

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def list_configs(self, user_id: int) -> list[PromptConfigDO]:
        """Return all saved prompt overrides for a user."""
        async with self._session_manager.session() as session:
            result = await session.execute(
                select(PromptConfigDO).where(PromptConfigDO.user_id == user_id)
            )
            return list(result.scalars().all())

    async def upsert_config(
        self,
        user_id: int,
        category: str,
        layer: str,
        content: str,
    ) -> PromptConfigDO:
        """Create or update a prompt override for (user_id, category, layer).

        Raises ValueError for invalid input.
        """
        if category not in VALID_CATEGORIES:
            raise ValueError(
                f"Invalid category '{category}'. Must be one of {sorted(VALID_CATEGORIES)}"
            )
        if not content or not content.strip():
            raise ValueError("content must not be empty or whitespace-only")
        if not _LAYER_RE.match(layer):
            raise ValueError(
                "layer must be 1-64 characters, alphanumeric and hyphens only"
            )

        async with self._session_manager.session() as session:
            stmt = (
                sqlite_insert(PromptConfigDO)
                .values(
                    user_id=user_id,
                    category=category,
                    layer=layer,
                    content=content,
                )
                .on_conflict_do_update(
                    index_elements=["user_id", "category", "layer"],
                    set_={"content": content},
                )
            )
            await session.execute(stmt)
            await session.commit()

            result = await session.execute(
                select(PromptConfigDO).where(
                    PromptConfigDO.user_id == user_id,
                    PromptConfigDO.category == category,
                    PromptConfigDO.layer == layer,
                )
            )
            row = result.scalar_one()
            logger.info(
                "Upserted prompt config: user_id=%d category=%s layer=%s",
                user_id,
                category,
                layer,
            )
            return row

    async def delete_config(self, user_id: int, category: str, layer: str) -> None:
        """Delete a user prompt override. Raises NotFoundError if no row exists.

        Raises ValueError for protected layers (ocr/default, summary/default,
        summary/common) — those layers are always present and cannot be removed.
        """
        if (category, layer) in PROTECTED_LAYERS:
            raise ValueError(
                f"{category}/{layer} is a protected layer and cannot be removed"
            )
        async with self._session_manager.session() as session:
            result = await session.execute(
                select(PromptConfigDO).where(
                    PromptConfigDO.user_id == user_id,
                    PromptConfigDO.category == category,
                    PromptConfigDO.layer == layer,
                )
            )
            row = result.scalar_one_or_none()
            if row is None:
                raise NotFoundError(f"No override found for {category}/{layer}")
            await session.execute(
                delete(PromptConfigDO).where(
                    PromptConfigDO.user_id == user_id,
                    PromptConfigDO.category == category,
                    PromptConfigDO.layer == layer,
                )
            )
            await session.commit()
            logger.info(
                "Deleted prompt config: user_id=%d category=%s layer=%s",
                user_id,
                category,
                layer,
            )

    # ------------------------------------------------------------------
    # Prompt resolution
    # ------------------------------------------------------------------

    async def get_effective_prompt(
        self,
        user_id: int,
        prompt_id: PromptId,
        note_type: str | None,
    ) -> str:
        """Return the effective composed prompt for the given user and note type.

        Composition:
          common = user override for 'common' OR loader default common (if any)
          specific = user override for note_type OR user override for 'default'
                     OR loader default for note_type OR loader default
          result = common + specific  (each part omitted when empty)
        """
        category = _PROMPT_ID_TO_CATEGORY[prompt_id.value]
        user_configs = await self.list_configs(user_id)
        user_map: dict[str, str] = {
            c.layer: c.content for c in user_configs if c.category == category
        }

        all_layers = self._prompt_loader.get_all_known_layers()
        file_map: dict[str, str] = all_layers.get(prompt_id.value, {})

        parts: list[str] = []

        # Common portion (present for summary, absent for OCR by default)
        common_text = user_map.get(COMMON) or file_map.get(COMMON, "")
        if common_text:
            parts.append(common_text)

        # Specific portion: type-specific override > default override > file type > file default
        specific_text: str | None = None
        if note_type:
            specific_text = user_map.get(note_type) or file_map.get(note_type)
        if specific_text is None:
            specific_text = user_map.get(DEFAULT) or file_map.get(DEFAULT)

        if specific_text:
            parts.append(specific_text)
        elif not parts:
            raise ValueError(
                f"No prompt content for {prompt_id.value} (note_type={note_type})"
            )

        return "\n\n".join(parts)

    async def compute_combined_prompt_hash(
        self, user_id: int, note_type: str | None
    ) -> str:
        """Return SHA-256 hex of (ocr_prompt + '|' + summary_prompt)."""
        ocr_prompt = await self.get_effective_prompt(
            user_id, PromptId.OCR_TRANSCRIPTION, note_type
        )
        summary_prompt = await self.get_effective_prompt(
            user_id, PromptId.SUMMARY_GENERATION, note_type
        )
        combined = ocr_prompt + "|" + summary_prompt
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # Merged view for the API
    # ------------------------------------------------------------------

    async def get_all_configs_with_defaults(
        self, user_id: int
    ) -> list[PromptConfigDTO]:
        """Return merged view: all known layers overlaid with user's DB rows.

        Each entry includes default_content (server file text) for Reset support.
        """
        user_configs = await self.list_configs(user_id)
        user_map: dict[tuple[str, str], str] = {
            (c.category, c.layer): c.content for c in user_configs
        }

        all_layers = self._prompt_loader.get_all_known_layers()

        result: list[PromptConfigDTO] = []
        for prompt_id_value, layer_map in all_layers.items():
            category = _PROMPT_ID_TO_CATEGORY.get(prompt_id_value)
            if category is None:
                continue
            for layer, default_text in layer_map.items():
                key = (category, layer)
                is_override = key in user_map
                content = user_map[key] if is_override else default_text
                result.append(
                    PromptConfigDTO(
                        category=category,
                        layer=layer,
                        content=content,
                        is_override=is_override,
                        default_content=default_text,
                    )
                )

        # Also include user-saved custom layers not in file loader
        for (category, layer), content in user_map.items():
            known_layers = all_layers.get(CATEGORY_MAP.get(category, ""), {})
            if layer not in known_layers:
                result.append(
                    PromptConfigDTO(
                        category=category,
                        layer=layer,
                        content=content,
                        is_override=True,
                        default_content=content,
                    )
                )

        return result

    def make_prompt_resolver(
        self, user_id: int, note_type: str | None
    ) -> Callable[[PromptId, str | None], "PromptConfigService"]:
        """Return a synchronous-style resolver suitable for async wrapping.

        Use this to create a resolver lambda for passing to processor modules.
        The returned callable is a coroutine factory — callers must await it.
        """

        async def resolver(prompt_id: PromptId, custom_type: str | None = None) -> str:
            return await self.get_effective_prompt(
                user_id, prompt_id, custom_type or note_type
            )

        return resolver  # type: ignore[return-value]
