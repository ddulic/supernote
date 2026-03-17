"""Routes for prompt configuration, staleness checking, and reprocessing."""

import logging
from pathlib import Path
from typing import cast

from aiohttp import web
from sqlalchemy import select

from supernote.models.base import BaseResponse, create_error_response
from supernote.models.prompt_config import (
    FileStalenessResponseVO,
    GetPromptsResponseVO,
    PageStalenessDTO,
    ReprocessRequestDTO,
    ReprocessResponseVO,
    UpsertPromptConfigDTO,
)
from supernote.server.db.models.file import UserFileDO
from supernote.server.db.models.note_processing import NotePageContentDO
from supernote.server.exceptions import SupernoteError
from supernote.server.services.processor import ProcessorService
from supernote.server.services.prompt_config import NotFoundError, PromptConfigService
from supernote.server.services.user import UserService

logger = logging.getLogger(__name__)

routes = web.RouteTableDef()


async def _get_user_id(request: web.Request) -> int | None:
    """Resolve the integer user_id from the authenticated request."""
    user_email: str = request["user"]
    user_service: UserService = request.app["user_service"]
    return await user_service.get_user_id(user_email)


async def _verify_file_ownership(
    request: web.Request, file_id: int, user_id: int
) -> UserFileDO | None:
    """Return the UserFileDO if it belongs to user_id, else None."""
    session_manager = request.app["session_manager"]
    async with session_manager.session() as session:
        file_do = cast(UserFileDO | None, await session.get(UserFileDO, file_id))
    if file_do is None or file_do.user_id != user_id:
        return None
    return file_do


# ---------------------------------------------------------------------------
# GET /api/extended/prompts
# ---------------------------------------------------------------------------


@routes.get("/api/extended/prompts")
async def handle_get_prompts(request: web.Request) -> web.Response:
    user_id = await _get_user_id(request)
    if not user_id:
        return web.json_response(
            create_error_response("User not found").to_dict(), status=404
        )

    prompt_config_service: PromptConfigService = request.app["prompt_config_service"]
    try:
        configs = await prompt_config_service.get_all_configs_with_defaults(user_id)
        return web.json_response(
            GetPromptsResponseVO(success=True, prompts=configs).to_dict()
        )
    except Exception as err:
        logger.exception("Error fetching prompts")
        return SupernoteError.uncaught(err).to_response()


# ---------------------------------------------------------------------------
# PUT /api/extended/prompts
# ---------------------------------------------------------------------------


@routes.put("/api/extended/prompts")
async def handle_put_prompt(request: web.Request) -> web.Response:
    user_id = await _get_user_id(request)
    if not user_id:
        return web.json_response(
            create_error_response("User not found").to_dict(), status=404
        )

    try:
        data = await request.json()
        dto = UpsertPromptConfigDTO.from_dict(data)
    except Exception as e:
        return web.json_response(
            create_error_response(f"Invalid request: {e}", "INVALID_INPUT").to_dict(),
            status=400,
        )

    prompt_config_service: PromptConfigService = request.app["prompt_config_service"]
    try:
        await prompt_config_service.upsert_config(
            user_id=user_id,
            category=dto.category,
            layer=dto.layer,
            content=dto.content,
        )
        return web.json_response(BaseResponse(success=True).to_dict())
    except ValueError as e:
        return web.json_response(
            create_error_response(str(e), "INVALID_INPUT").to_dict(), status=400
        )
    except Exception as err:
        logger.exception("Error saving prompt config")
        return SupernoteError.uncaught(err).to_response()


# ---------------------------------------------------------------------------
# DELETE /api/extended/prompts/{category}/{layer}
# ---------------------------------------------------------------------------


@routes.delete("/api/extended/prompts/{category}/{layer}")
async def handle_delete_prompt(request: web.Request) -> web.Response:
    user_id = await _get_user_id(request)
    if not user_id:
        return web.json_response(
            create_error_response("User not found").to_dict(), status=404
        )

    category = request.match_info["category"]
    layer = request.match_info["layer"]

    prompt_config_service: PromptConfigService = request.app["prompt_config_service"]
    try:
        await prompt_config_service.delete_config(
            user_id=user_id, category=category, layer=layer
        )
        return web.json_response(BaseResponse(success=True).to_dict())
    except ValueError as e:
        return web.json_response(
            create_error_response(str(e), "PROTECTED_LAYER").to_dict(),
            status=400,
        )
    except NotFoundError:
        return web.json_response(
            create_error_response(
                f"No override found for {category}/{layer}", "NOT_FOUND"
            ).to_dict(),
            status=404,
        )
    except Exception as err:
        logger.exception("Error deleting prompt config")
        return SupernoteError.uncaught(err).to_response()


# ---------------------------------------------------------------------------
# GET /api/extended/files/{file_id}/staleness
# ---------------------------------------------------------------------------


@routes.get("/api/extended/files/{file_id}/staleness")
async def handle_get_staleness(request: web.Request) -> web.Response:
    user_id = await _get_user_id(request)
    if not user_id:
        return web.json_response(
            create_error_response("User not found").to_dict(), status=404
        )

    try:
        file_id = int(request.match_info["file_id"])
    except ValueError:
        return web.json_response(
            create_error_response("Invalid file_id", "INVALID_INPUT").to_dict(),
            status=400,
        )

    file_do = await _verify_file_ownership(request, file_id, user_id)
    if file_do is None:
        return web.json_response(
            create_error_response(
                "File not found or access denied", "NOT_FOUND"
            ).to_dict(),
            status=403,
        )

    prompt_config_service: PromptConfigService = request.app["prompt_config_service"]
    session_manager = request.app["session_manager"]

    try:
        note_type = Path(file_do.file_name).stem.lower() if file_do.file_name else None
        current_hash = await prompt_config_service.compute_combined_prompt_hash(
            user_id=user_id, note_type=note_type
        )

        async with session_manager.session() as session:
            stmt = (
                select(NotePageContentDO)
                .where(NotePageContentDO.file_id == file_id)
                .order_by(NotePageContentDO.page_index)
            )
            result = await session.execute(stmt)
            pages = list(result.scalars().all())

        page_dtos = []
        stale_count = 0
        for p in pages:
            is_stale = p.prompt_hash != current_hash
            if is_stale:
                stale_count += 1
            page_dtos.append(
                PageStalenessDTO(
                    page_id=p.page_id or "",
                    page_index=p.page_index,
                    stored_hash=p.prompt_hash,
                    is_stale=is_stale,
                )
            )

        return web.json_response(
            FileStalenessResponseVO(
                success=True,
                current_prompt_hash=current_hash,
                pages=page_dtos,
                stale_count=stale_count,
                total_count=len(page_dtos),
            ).to_dict()
        )
    except Exception as err:
        logger.exception("Error computing staleness")
        return SupernoteError.uncaught(err).to_response()


# ---------------------------------------------------------------------------
# POST /api/extended/files/{file_id}/reprocess
# ---------------------------------------------------------------------------


@routes.post("/api/extended/files/{file_id}/reprocess")
async def handle_reprocess_file(request: web.Request) -> web.Response:
    user_id = await _get_user_id(request)
    if not user_id:
        return web.json_response(
            create_error_response("User not found").to_dict(), status=404
        )

    try:
        file_id = int(request.match_info["file_id"])
    except ValueError:
        return web.json_response(
            create_error_response("Invalid file_id", "INVALID_INPUT").to_dict(),
            status=400,
        )

    file_do = await _verify_file_ownership(request, file_id, user_id)
    if file_do is None:
        return web.json_response(
            create_error_response(
                "File not found or access denied", "NOT_FOUND"
            ).to_dict(),
            status=403,
        )

    # Parse optional request body
    requested_page_ids: list[str] | None = None
    try:
        body = await request.read()
        if body:
            dto = ReprocessRequestDTO.from_json(body.decode())
            requested_page_ids = dto.page_ids
    except Exception:
        pass  # Body is optional; ignore parse errors

    prompt_config_service: PromptConfigService = request.app["prompt_config_service"]
    processor_service: ProcessorService = request.app["processor_service"]
    session_manager = request.app["session_manager"]

    try:
        note_type = Path(file_do.file_name).stem.lower() if file_do.file_name else None
        current_hash = await prompt_config_service.compute_combined_prompt_hash(
            user_id=user_id, note_type=note_type
        )

        # Determine which pages to reprocess
        async with session_manager.session() as session:
            stmt = (
                select(NotePageContentDO)
                .where(NotePageContentDO.file_id == file_id)
                .order_by(NotePageContentDO.page_index)
            )
            result = await session.execute(stmt)
            pages = list(result.scalars().all())

        stale_page_ids = [
            p.page_id for p in pages if p.page_id and p.prompt_hash != current_hash
        ]

        if requested_page_ids is not None:
            # Filter to only stale pages from the requested list
            stale_set = set(stale_page_ids)
            page_ids_to_reprocess = [
                pid for pid in requested_page_ids if pid in stale_set
            ]
        else:
            page_ids_to_reprocess = stale_page_ids

        if not page_ids_to_reprocess:
            return web.json_response(
                ReprocessResponseVO(success=True, queued_page_count=0).to_dict()
            )

        # Check if already processing
        if file_id in processor_service.processing_files:
            return web.json_response(
                create_error_response(
                    "This file is already queued for processing", "ALREADY_PROCESSING"
                ).to_dict(),
                status=409,
            )

        count = await processor_service.reprocess_pages(
            file_id=file_id, page_ids=page_ids_to_reprocess
        )
        return web.json_response(
            ReprocessResponseVO(success=True, queued_page_count=count).to_dict()
        )
    except Exception as err:
        logger.exception("Error triggering reprocess")
        return SupernoteError.uncaught(err).to_response()


# ---------------------------------------------------------------------------
# POST /api/extended/files/{file_id}/pages/{page_id}/reprocess
# ---------------------------------------------------------------------------


@routes.post("/api/extended/files/{file_id}/pages/{page_id}/reprocess")
async def handle_reprocess_page(request: web.Request) -> web.Response:
    user_id = await _get_user_id(request)
    if not user_id:
        return web.json_response(
            create_error_response("User not found").to_dict(), status=404
        )

    try:
        file_id = int(request.match_info["file_id"])
    except ValueError:
        return web.json_response(
            create_error_response("Invalid file_id", "INVALID_INPUT").to_dict(),
            status=400,
        )

    page_id = request.match_info["page_id"]

    file_do = await _verify_file_ownership(request, file_id, user_id)
    if file_do is None:
        return web.json_response(
            create_error_response(
                "File not found or access denied", "NOT_FOUND"
            ).to_dict(),
            status=403,
        )

    prompt_config_service: PromptConfigService = request.app["prompt_config_service"]
    processor_service: ProcessorService = request.app["processor_service"]
    session_manager = request.app["session_manager"]

    try:
        note_type = Path(file_do.file_name).stem.lower() if file_do.file_name else None
        current_hash = await prompt_config_service.compute_combined_prompt_hash(
            user_id=user_id, note_type=note_type
        )

        async with session_manager.session() as session:
            stmt = select(NotePageContentDO).where(
                NotePageContentDO.file_id == file_id,
                NotePageContentDO.page_id == page_id,
            )
            result = await session.execute(stmt)
            page = result.scalar_one_or_none()

        if page is None:
            return web.json_response(
                create_error_response("Page not found", "NOT_FOUND").to_dict(),
                status=404,
            )

        if page.prompt_hash == current_hash:
            return web.json_response(
                create_error_response(
                    "This page does not require reprocessing", "NOT_STALE"
                ).to_dict(),
                status=400,
            )

        count = await processor_service.reprocess_pages(
            file_id=file_id, page_ids=[page_id]
        )
        return web.json_response(
            ReprocessResponseVO(success=True, queued_page_count=count).to_dict()
        )
    except Exception as err:
        logger.exception("Error triggering page reprocess")
        return SupernoteError.uncaught(err).to_response()


# ---------------------------------------------------------------------------
# POST /api/extended/reprocess-all
# ---------------------------------------------------------------------------


@routes.post("/api/extended/reprocess-all")
async def handle_reprocess_all(request: web.Request) -> web.Response:
    user_id = await _get_user_id(request)
    if not user_id:
        return web.json_response(
            create_error_response("Unauthorized", "UNAUTHORIZED").to_dict(), status=401
        )
    try:
        processor_service: ProcessorService = request.app["processor_service"]
        count = await processor_service.reprocess_all(user_id=user_id)
        return web.json_response(
            ReprocessResponseVO(success=True, queued_page_count=count).to_dict()
        )
    except Exception as err:
        logger.exception("Error triggering reprocess all")
        return SupernoteError.uncaught(err).to_response()
