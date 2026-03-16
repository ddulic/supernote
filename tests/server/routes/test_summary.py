from unittest.mock import AsyncMock, patch

import pytest
from aiohttp.test_utils import TestClient

from supernote.client.client import Client
from supernote.client.summary import SummaryClient
from supernote.models.summary import (
    AddSummaryDTO,
    AddSummaryGroupDTO,
    QuerySummaryDTO,
    UpdateSummaryDTO,
    UpdateSummaryGroupDTO,
)
from supernote.server.exceptions import SupernoteError


@pytest.fixture
def summary_client(authenticated_client: Client) -> SummaryClient:
    """Create a SummaryClient."""
    return SummaryClient(authenticated_client)


async def test_summary_tags_crud(summary_client: SummaryClient) -> None:
    # 1. Query initial tags (should be empty)
    response = await summary_client.query_tags()
    assert response.success
    assert len(response.summary_tag_do_list) == 0

    # 2. Add a tag
    add_response = await summary_client.add_tag(name="Work")
    assert add_response.success
    tag_id = add_response.id
    assert tag_id is not None

    # 3. Verify tag was added
    response = await summary_client.query_tags()
    assert len(response.summary_tag_do_list) == 1
    assert response.summary_tag_do_list[0].name == "Work"
    assert response.summary_tag_do_list[0].id == tag_id

    # 4. Update the tag
    update_response = await summary_client.update_tag(tag_id=tag_id, name="Job")
    assert update_response.success

    # 5. Verify update
    response = await summary_client.query_tags()
    assert response.summary_tag_do_list[0].name == "Job"

    # 6. Delete the tag
    delete_response = await summary_client.delete_tag(tag_id=tag_id)
    assert delete_response.success

    # 7. Verify deletion
    response = await summary_client.query_tags()
    assert len(response.summary_tag_do_list) == 0


async def test_summary_crud(summary_client: SummaryClient) -> None:
    # 1. Add a summary
    add_dto = AddSummaryDTO(
        content="This is a test summary",
        data_source="TEST",
        tags="test,summary",
        metadata='{"key": "value"}',
    )
    add_response = await summary_client.add_summary(add_dto)
    assert add_response.success
    summary_id = add_response.id
    assert summary_id is not None

    # 2. Query the summary
    query_response = await summary_client.query_summaries(ids=[summary_id])
    assert query_response.success
    assert len(query_response.summary_do_list) == 1
    summary = query_response.summary_do_list[0]
    assert summary.content == "This is a test summary"
    assert summary.data_source == "TEST"
    assert summary.tags == "test,summary"
    assert summary.metadata == '{"key": "value"}'

    # 3. Update the summary
    update_dto = UpdateSummaryDTO(
        id=summary_id,
        content="Updated test summary",
        tags="updated",
    )
    update_response = await summary_client.update_summary(update_dto)
    assert update_response.success

    # 4. Verify update
    query_response = await summary_client.query_summaries(ids=[summary_id])
    summary = query_response.summary_do_list[0]
    assert summary.content == "Updated test summary"
    assert summary.tags == "updated"

    # 5. Delete the summary
    delete_response = await summary_client.delete_summary(summary_id)
    assert delete_response.success

    # 6. Verify deletion
    query_response = await summary_client.query_summaries(ids=[summary_id])
    assert len(query_response.summary_do_list) == 0


async def test_group_crud(summary_client: SummaryClient) -> None:
    # 1. Add a group
    group_uuid = "test-group-uuid"
    add_dto = AddSummaryGroupDTO(
        unique_identifier=group_uuid,
        name="Test Group",
        md5_hash="hash123",
        description="A test group",
    )
    add_response = await summary_client.add_group(add_dto)
    assert add_response.success
    group_id = add_response.id
    assert group_id is not None

    # 2. Query groups
    query_response = await summary_client.query_groups()
    assert query_response.success
    assert [
        (g.id, g.unique_identifier, g.name) for g in query_response.summary_do_list
    ] == [(group_id, group_uuid, "Test Group")]

    # 3. Update group
    update_dto = UpdateSummaryGroupDTO(
        id=group_id,
        unique_identifier=group_uuid,
        name="Updated Group",
        md5_hash="newhash",
    )
    update_response = await summary_client.update_group(update_dto)
    assert update_response.success

    # 4. Verify update
    query_response = await summary_client.query_groups()
    assert [
        (g.id, g.unique_identifier, g.name) for g in query_response.summary_do_list
    ] == [(group_id, group_uuid, "Updated Group")]

    # 5. Delete group
    delete_response = await summary_client.delete_group(group_id)
    assert delete_response.success

    # 6. Verify deletion
    query_response = await summary_client.query_groups()
    assert not any(g.id == group_id for g in query_response.summary_do_list)


async def test_summary_binary_flow(summary_client: SummaryClient) -> None:
    # 1. Apply for upload
    upload_response = await summary_client.upload_apply("test_strokes.bin")
    assert upload_response.success
    assert upload_response.full_upload_url is not None
    assert upload_response.inner_name is not None
    inner_name = upload_response.inner_name

    # 2. Add summary with that inner name
    add_dto = AddSummaryDTO(
        content="Summary with binary",
        data_source="TEST",
        handwrite_inner_name=inner_name,
    )
    add_response = await summary_client.add_summary(add_dto)
    assert add_response.id
    summary_id = add_response.id

    # 3. Apply for download
    download_response = await summary_client.download_summary(summary_id)
    assert download_response.success
    assert download_response.url is not None
    assert inner_name in download_response.url


async def test_advanced_queries(summary_client: SummaryClient) -> None:
    # 1. Setup: Add a test summary
    add_dto = AddSummaryDTO(
        content="Advanced Test content",
        md5_hash="advhash",
        handwrite_md5="advhwmd5",
        comment_handwrite_name="advhw.bin",
    )
    add_response = await summary_client.add_summary(add_dto)
    summary_id = add_response.id
    assert summary_id is not None

    # 2. Test query/summary/hash
    query_dto = QuerySummaryDTO(ids=[summary_id])
    hash_response = await summary_client.query_summary_hash(query_dto)
    assert hash_response.success
    assert len(hash_response.summary_info_vo_list) == 1
    info = hash_response.summary_info_vo_list[0]
    assert info.id == summary_id
    assert info.md5_hash == "advhash"
    assert info.handwrite_md5 == "advhwmd5"
    assert info.comment_handwrite_name == "advhw.bin"

    # 3. Test query/summary/id
    id_response = await summary_client.query_summary_id(query_dto)
    assert id_response.success
    assert len(id_response.summary_do_list) == 1
    summary = id_response.summary_do_list[0]
    assert summary.id == summary_id
    assert summary.content == "Advanced Test content"


# ---------------------------------------------------------------------------
# Error path tests — patch service methods to raise exceptions
# ---------------------------------------------------------------------------

_PATCH_BASE = "supernote.server.services.summary.SummaryService"


async def test_add_tag_supernote_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_PATCH_BASE}.add_tag", new_callable=AsyncMock) as m:
        m.side_effect = SupernoteError("tag error")
        resp = await client.post(
            "/api/file/add/summary/tag", json={"name": "x"}, headers=auth_headers
        )
    assert resp.status == 400


async def test_add_tag_generic_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_PATCH_BASE}.add_tag", new_callable=AsyncMock) as m:
        m.side_effect = RuntimeError("boom")
        resp = await client.post(
            "/api/file/add/summary/tag", json={"name": "x"}, headers=auth_headers
        )
    assert resp.status == 500


async def test_update_tag_supernote_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_PATCH_BASE}.update_tag", new_callable=AsyncMock) as m:
        m.side_effect = SupernoteError("not found", status_code=404)
        resp = await client.post(
            "/api/file/update/summary/tag",
            json={"id": 99, "name": "x"},
            headers=auth_headers,
        )
    assert resp.status == 404


async def test_update_tag_generic_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_PATCH_BASE}.update_tag", new_callable=AsyncMock) as m:
        m.side_effect = RuntimeError("boom")
        resp = await client.post(
            "/api/file/update/summary/tag",
            json={"id": 99, "name": "x"},
            headers=auth_headers,
        )
    assert resp.status == 500


async def test_delete_tag_supernote_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_PATCH_BASE}.delete_tag", new_callable=AsyncMock) as m:
        m.side_effect = SupernoteError("not found", status_code=404)
        resp = await client.post(
            "/api/file/delete/summary/tag", json={"id": 99}, headers=auth_headers
        )
    assert resp.status == 404


async def test_delete_tag_generic_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_PATCH_BASE}.delete_tag", new_callable=AsyncMock) as m:
        m.side_effect = RuntimeError("boom")
        resp = await client.post(
            "/api/file/delete/summary/tag", json={"id": 99}, headers=auth_headers
        )
    assert resp.status == 500


async def test_query_tags_supernote_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_PATCH_BASE}.list_tags", new_callable=AsyncMock) as m:
        m.side_effect = SupernoteError("error")
        resp = await client.post(
            "/api/file/query/summary/tag", json={}, headers=auth_headers
        )
    assert resp.status == 400


async def test_query_tags_generic_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_PATCH_BASE}.list_tags", new_callable=AsyncMock) as m:
        m.side_effect = RuntimeError("boom")
        resp = await client.post(
            "/api/file/query/summary/tag", json={}, headers=auth_headers
        )
    assert resp.status == 500


async def test_add_summary_supernote_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_PATCH_BASE}.add_summary", new_callable=AsyncMock) as m:
        m.side_effect = SupernoteError("error")
        resp = await client.post(
            "/api/file/add/summary",
            json={"content": "x", "data_source": "TEST"},
            headers=auth_headers,
        )
    assert resp.status == 400


async def test_add_summary_generic_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_PATCH_BASE}.add_summary", new_callable=AsyncMock) as m:
        m.side_effect = RuntimeError("boom")
        resp = await client.post(
            "/api/file/add/summary",
            json={"content": "x", "data_source": "TEST"},
            headers=auth_headers,
        )
    assert resp.status == 500


async def test_update_summary_supernote_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_PATCH_BASE}.update_summary", new_callable=AsyncMock) as m:
        m.side_effect = SupernoteError("error")
        resp = await client.post(
            "/api/file/update/summary",
            json={"id": 99, "content": "x"},
            headers=auth_headers,
        )
    assert resp.status == 400


async def test_update_summary_generic_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_PATCH_BASE}.update_summary", new_callable=AsyncMock) as m:
        m.side_effect = RuntimeError("boom")
        resp = await client.post(
            "/api/file/update/summary",
            json={"id": 99, "content": "x"},
            headers=auth_headers,
        )
    assert resp.status == 500


async def test_delete_summary_supernote_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_PATCH_BASE}.delete_summary", new_callable=AsyncMock) as m:
        m.side_effect = SupernoteError("error")
        resp = await client.post(
            "/api/file/delete/summary", json={"id": 99}, headers=auth_headers
        )
    assert resp.status == 400


async def test_delete_summary_generic_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_PATCH_BASE}.delete_summary", new_callable=AsyncMock) as m:
        m.side_effect = RuntimeError("boom")
        resp = await client.post(
            "/api/file/delete/summary", json={"id": 99}, headers=auth_headers
        )
    assert resp.status == 500


async def test_query_summaries_supernote_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_PATCH_BASE}.list_summaries", new_callable=AsyncMock) as m:
        m.side_effect = SupernoteError("error")
        resp = await client.post(
            "/api/file/query/summary", json={}, headers=auth_headers
        )
    assert resp.status == 400


async def test_query_summaries_generic_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_PATCH_BASE}.list_summaries", new_callable=AsyncMock) as m:
        m.side_effect = RuntimeError("boom")
        resp = await client.post(
            "/api/file/query/summary", json={}, headers=auth_headers
        )
    assert resp.status == 500


async def test_add_group_supernote_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_PATCH_BASE}.add_group", new_callable=AsyncMock) as m:
        m.side_effect = SupernoteError("error")
        resp = await client.post(
            "/api/file/add/summary/group",
            json={"uniqueIdentifier": "uid", "name": "g", "md5Hash": "h"},
            headers=auth_headers,
        )
    assert resp.status == 400


async def test_add_group_generic_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_PATCH_BASE}.add_group", new_callable=AsyncMock) as m:
        m.side_effect = RuntimeError("boom")
        resp = await client.post(
            "/api/file/add/summary/group",
            json={"uniqueIdentifier": "uid", "name": "g", "md5Hash": "h"},
            headers=auth_headers,
        )
    assert resp.status == 500


async def test_update_group_supernote_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_PATCH_BASE}.update_group", new_callable=AsyncMock) as m:
        m.side_effect = SupernoteError("error")
        resp = await client.post(
            "/api/file/update/summary/group",
            json={"id": 1, "uniqueIdentifier": "uid", "name": "g", "md5Hash": "h"},
            headers=auth_headers,
        )
    assert resp.status == 400


async def test_update_group_generic_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_PATCH_BASE}.update_group", new_callable=AsyncMock) as m:
        m.side_effect = RuntimeError("boom")
        resp = await client.post(
            "/api/file/update/summary/group",
            json={"id": 1, "uniqueIdentifier": "uid", "name": "g", "md5Hash": "h"},
            headers=auth_headers,
        )
    assert resp.status == 500


async def test_delete_group_supernote_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_PATCH_BASE}.delete_group", new_callable=AsyncMock) as m:
        m.side_effect = SupernoteError("error")
        resp = await client.post(
            "/api/file/delete/summary/group", json={"id": 99}, headers=auth_headers
        )
    assert resp.status == 400


async def test_delete_group_generic_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_PATCH_BASE}.delete_group", new_callable=AsyncMock) as m:
        m.side_effect = RuntimeError("boom")
        resp = await client.post(
            "/api/file/delete/summary/group", json={"id": 99}, headers=auth_headers
        )
    assert resp.status == 500


async def test_query_groups_supernote_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_PATCH_BASE}.list_groups", new_callable=AsyncMock) as m:
        m.side_effect = SupernoteError("error")
        resp = await client.post(
            "/api/file/query/summary/group", json={}, headers=auth_headers
        )
    assert resp.status == 400


async def test_query_groups_generic_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_PATCH_BASE}.list_groups", new_callable=AsyncMock) as m:
        m.side_effect = RuntimeError("boom")
        resp = await client.post(
            "/api/file/query/summary/group", json={}, headers=auth_headers
        )
    assert resp.status == 500


async def test_upload_apply_summary_generic_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(
        "supernote.server.utils.url_signer.UrlSigner.sign", new_callable=AsyncMock
    ) as m:
        m.side_effect = RuntimeError("boom")
        resp = await client.post(
            "/api/file/upload/apply/summary",
            json={"file_name": "test.bin", "equipment_no": "EQ1"},
            headers=auth_headers,
        )
    assert resp.status == 500


async def test_download_summary_no_handwrite_inner_name(
    client: TestClient, auth_headers: dict[str, str], summary_client: SummaryClient
) -> None:
    """Downloading a summary with no handwrite_inner_name returns 404."""
    add_dto = AddSummaryDTO(content="no binary", data_source="TEST")
    add_resp = await summary_client.add_summary(add_dto)
    summary_id = add_resp.id
    assert summary_id

    resp = await client.post(
        "/api/file/download/summary", json={"id": summary_id}, headers=auth_headers
    )
    assert resp.status == 404


async def test_download_summary_supernote_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_PATCH_BASE}.get_summary", new_callable=AsyncMock) as m:
        m.side_effect = SupernoteError("not found", status_code=404)
        resp = await client.post(
            "/api/file/download/summary", json={"id": 99}, headers=auth_headers
        )
    assert resp.status == 404


async def test_download_summary_generic_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_PATCH_BASE}.get_summary", new_callable=AsyncMock) as m:
        m.side_effect = RuntimeError("boom")
        resp = await client.post(
            "/api/file/download/summary", json={"id": 99}, headers=auth_headers
        )
    assert resp.status == 500


async def test_query_summary_hash_supernote_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_PATCH_BASE}.list_summary_infos", new_callable=AsyncMock) as m:
        m.side_effect = SupernoteError("error")
        resp = await client.post(
            "/api/file/query/summary/hash", json={}, headers=auth_headers
        )
    assert resp.status == 400


async def test_query_summary_hash_generic_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_PATCH_BASE}.list_summary_infos", new_callable=AsyncMock) as m:
        m.side_effect = RuntimeError("boom")
        resp = await client.post(
            "/api/file/query/summary/hash", json={}, headers=auth_headers
        )
    assert resp.status == 500


async def test_query_summary_by_id_supernote_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_PATCH_BASE}.list_summaries_by_id", new_callable=AsyncMock) as m:
        m.side_effect = SupernoteError("error")
        resp = await client.post(
            "/api/file/query/summary/id", json={}, headers=auth_headers
        )
    assert resp.status == 400


async def test_query_summary_by_id_generic_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_PATCH_BASE}.list_summaries_by_id", new_callable=AsyncMock) as m:
        m.side_effect = RuntimeError("boom")
        resp = await client.post(
            "/api/file/query/summary/id", json={}, headers=auth_headers
        )
    assert resp.status == 500
