"""Tests for prompt-aware processing and reprocess functionality."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select

from supernote.models.base import ProcessingStatus
from supernote.server.db.models.file import UserFileDO
from supernote.server.db.models.note_processing import NotePageContentDO, SystemTaskDO
from supernote.server.db.session import DatabaseSessionManager
from supernote.server.services.processor import ProcessorService
from supernote.server.services.processor_modules.ocr import OcrModule
from supernote.server.services.processor_modules.summary import SummaryModule
from supernote.server.services.prompt_config import PromptConfigService
from supernote.server.utils.prompt_loader import PromptId, PromptLoader

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def prompt_loader() -> PromptLoader:
    return PromptLoader()


@pytest.fixture
def prompt_config_service(
    session_manager: DatabaseSessionManager, prompt_loader: PromptLoader
) -> PromptConfigService:
    return PromptConfigService(session_manager, prompt_loader)


# ---------------------------------------------------------------------------
# OCR Module: prompt_hash written to DB
# ---------------------------------------------------------------------------


async def _seed_file_and_page(
    session_manager: DatabaseSessionManager,
    file_id: int,
    page_id: str,
    file_name: str = "monthly.note",
) -> None:
    """Seed minimal UserFileDO and NotePageContentDO rows."""
    async with session_manager.session() as session:
        file_do = UserFileDO(
            id=file_id,
            user_id=1,
            file_name=file_name,
            is_folder="N",
        )
        content_do = NotePageContentDO(
            file_id=file_id,
            page_index=0,
            page_id=page_id,
        )
        session.add(file_do)
        session.add(content_do)
        await session.commit()


async def test_ocr_module_writes_prompt_hash(
    session_manager: DatabaseSessionManager,
) -> None:
    """OCR module writes prompt_hash to NotePageContentDO when provided."""
    file_id = 1
    page_id = "P001"
    await _seed_file_and_page(session_manager, file_id, page_id)

    ai_service = MagicMock()
    ai_service.is_configured = True
    ai_service.ocr_image = AsyncMock(return_value="Extracted text")

    file_service = MagicMock()
    blob_storage = MagicMock()
    blob_storage.exists = AsyncMock(return_value=True)
    blob_storage.get = MagicMock(return_value=aiter_bytes(b"png_data"))
    file_service.blob_storage = blob_storage

    ocr_module = OcrModule(file_service=file_service, ai_service=ai_service)

    async def mock_prompt_resolver(
        prompt_id: PromptId, custom_type: str | None = None
    ) -> str:
        return "Custom OCR prompt"

    test_hash = "abc123deadbeef"

    await ocr_module.process(
        file_id=file_id,
        session_manager=session_manager,
        page_index=0,
        page_id=page_id,
        prompt_resolver=mock_prompt_resolver,
        prompt_hash=test_hash,
    )

    # Verify hash was written to DB
    async with session_manager.session() as session:
        stmt = select(NotePageContentDO).where(
            NotePageContentDO.file_id == file_id,
            NotePageContentDO.page_id == page_id,
        )
        result = await session.execute(stmt)
        row = result.scalar_one()
    assert row.prompt_hash == test_hash


async def test_ocr_module_no_hash_when_not_provided(
    session_manager: DatabaseSessionManager,
) -> None:
    """OCR module leaves prompt_hash as None when not provided."""
    file_id = 2
    page_id = "P002"
    await _seed_file_and_page(session_manager, file_id, page_id)

    ai_service = MagicMock()
    ai_service.is_configured = True
    ai_service.ocr_image = AsyncMock(return_value="Extracted text")

    file_service = MagicMock()
    blob_storage = MagicMock()
    blob_storage.exists = AsyncMock(return_value=True)
    blob_storage.get = MagicMock(return_value=aiter_bytes(b"png_data"))
    file_service.blob_storage = blob_storage

    ocr_module = OcrModule(file_service=file_service, ai_service=ai_service)

    # No prompt_resolver or prompt_hash passed
    await ocr_module.process(
        file_id=file_id,
        session_manager=session_manager,
        page_index=0,
        page_id=page_id,
    )

    async with session_manager.session() as session:
        stmt = select(NotePageContentDO).where(
            NotePageContentDO.file_id == file_id,
            NotePageContentDO.page_id == page_id,
        )
        result = await session.execute(stmt)
        row = result.scalar_one()
    assert row.prompt_hash is None


# ---------------------------------------------------------------------------
# ProcessorService: passes prompt_resolver + prompt_hash to modules
# ---------------------------------------------------------------------------


async def test_processor_service_passes_resolver_to_modules(
    prompt_config_service: PromptConfigService,
) -> None:
    """ProcessorService passes prompt_resolver and prompt_hash when prompt_config_service set."""
    from supernote.server.services.processor_modules.embedding import EmbeddingModule
    from supernote.server.services.processor_modules.page_hashing import (
        PageHashingModule,
    )
    from supernote.server.services.processor_modules.png_conversion import (
        PngConversionModule,
    )

    event_bus = MagicMock()
    session_manager = MagicMock()
    file_service = MagicMock()
    summary_service = MagicMock()

    # Mock the file lookup inside process_file
    file_do = MagicMock()
    file_do.user_id = 42
    file_do.file_name = "monthly.note"

    mock_session = AsyncMock()
    mock_session.get.return_value = file_do
    mock_result = MagicMock()
    mock_result.all.return_value = [(0, "p0")]
    mock_session.execute.return_value = mock_result

    session_manager.session.return_value.__aenter__.return_value = mock_session

    processor = ProcessorService(
        event_bus=event_bus,
        session_manager=session_manager,
        file_service=file_service,
        summary_service=summary_service,
        prompt_config_service=prompt_config_service,
    )

    hashing = MagicMock(spec=PageHashingModule)
    hashing.run = AsyncMock(return_value=True)
    png = MagicMock(spec=PngConversionModule)
    png.run = AsyncMock(return_value=True)
    ocr = MagicMock(spec=OcrModule)
    ocr.run = AsyncMock(return_value=True)
    embedding = MagicMock(spec=EmbeddingModule)
    embedding.run = AsyncMock(return_value=True)
    summary = MagicMock(spec=SummaryModule)
    summary.run = AsyncMock(return_value=True)

    processor.register_modules(
        hashing=hashing, png=png, ocr=ocr, embedding=embedding, summary=summary
    )

    await processor.process_file(file_id=99)

    # OCR should have been called with prompt_resolver and prompt_hash kwargs
    ocr_call_kwargs = ocr.run.call_args.kwargs
    assert "prompt_resolver" in ocr_call_kwargs
    assert "prompt_hash" in ocr_call_kwargs
    assert ocr_call_kwargs["prompt_hash"] is not None
    assert len(ocr_call_kwargs["prompt_hash"]) == 64  # sha256 hex


# ---------------------------------------------------------------------------
# reprocess_pages
# ---------------------------------------------------------------------------


async def test_reprocess_pages_resets_tasks(
    session_manager: DatabaseSessionManager,
    prompt_config_service: PromptConfigService,
) -> None:
    """reprocess_pages resets SystemTaskDO status to PENDING for specified pages."""
    file_id = 10
    page_id = "P010"

    # Seed completed OCR and embedding tasks for the page
    async with session_manager.session() as session:
        ocr_task = SystemTaskDO(
            file_id=file_id,
            task_type="OCR_EXTRACTION",
            key=page_id,
            status=ProcessingStatus.COMPLETED,
        )
        embed_task = SystemTaskDO(
            file_id=file_id,
            task_type="EMBEDDING_GENERATION",
            key=page_id,
            status=ProcessingStatus.COMPLETED,
        )
        summary_task = SystemTaskDO(
            file_id=file_id,
            task_type="SUMMARY_GENERATION",
            key="global",
            status=ProcessingStatus.COMPLETED,
        )
        session.add_all([ocr_task, embed_task, summary_task])
        await session.commit()

    event_bus = MagicMock()
    file_service = MagicMock()
    summary_service = MagicMock()
    processor = ProcessorService(
        event_bus=event_bus,
        session_manager=session_manager,
        file_service=file_service,
        summary_service=summary_service,
        prompt_config_service=prompt_config_service,
    )

    count = await processor.reprocess_pages(file_id=file_id, page_ids=[page_id])
    assert count == 1

    # Check that task statuses were reset
    async with session_manager.session() as session:
        for task_type, key in [
            ("OCR_EXTRACTION", page_id),
            ("EMBEDDING_GENERATION", page_id),
            ("SUMMARY_GENERATION", "global"),
        ]:
            stmt = select(SystemTaskDO).where(
                SystemTaskDO.file_id == file_id,
                SystemTaskDO.task_type == task_type,
                SystemTaskDO.key == key,
            )
            result = await session.execute(stmt)
            task = result.scalar_one()
            assert task.status == ProcessingStatus.PENDING, (
                f"{task_type}/{key} expected PENDING got {task.status}"
            )


async def test_reprocess_pages_empty_list_does_nothing(
    session_manager: DatabaseSessionManager,
    prompt_config_service: PromptConfigService,
) -> None:
    """reprocess_pages with empty list returns 0."""
    event_bus = MagicMock()
    processor = ProcessorService(
        event_bus=event_bus,
        session_manager=session_manager,
        file_service=MagicMock(),
        summary_service=MagicMock(),
        prompt_config_service=prompt_config_service,
    )
    count = await processor.reprocess_pages(file_id=99, page_ids=[])
    assert count == 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def aiter_bytes_gen(data: bytes):  # type: ignore[no-untyped-def]
    yield data


def aiter_bytes(data: bytes):  # type: ignore[no-untyped-def]
    return aiter_bytes_gen(data)
