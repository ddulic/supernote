"""Error-path tests for file_web routes.

Tests the SupernoteError and generic Exception handler blocks
in file_web.py by patching FileService methods.
"""

from unittest.mock import AsyncMock, patch

from aiohttp.test_utils import TestClient

from supernote.server.exceptions import SupernoteError

_FS = "supernote.server.services.file.FileService"


async def test_capacity_query_supernote_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_FS}.get_storage_usage", new_callable=AsyncMock) as m:
        m.side_effect = SupernoteError("error")
        resp = await client.post(
            "/api/file/capacity/query", json={}, headers=auth_headers
        )
    assert resp.status == 400


async def test_capacity_query_generic_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_FS}.get_storage_usage", new_callable=AsyncMock) as m:
        m.side_effect = RuntimeError("boom")
        resp = await client.post(
            "/api/file/capacity/query", json={}, headers=auth_headers
        )
    assert resp.status == 500


async def test_recycle_list_supernote_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_FS}.list_recycle", new_callable=AsyncMock) as m:
        m.side_effect = SupernoteError("error")
        resp = await client.post(
            "/api/file/recycle/list/query", json={}, headers=auth_headers
        )
    assert resp.status == 400


async def test_recycle_list_generic_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_FS}.list_recycle", new_callable=AsyncMock) as m:
        m.side_effect = RuntimeError("boom")
        resp = await client.post(
            "/api/file/recycle/list/query", json={}, headers=auth_headers
        )
    assert resp.status == 500


async def test_recycle_delete_supernote_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_FS}.delete_from_recycle", new_callable=AsyncMock) as m:
        m.side_effect = SupernoteError("error")
        resp = await client.post(
            "/api/file/recycle/delete", json={"idList": []}, headers=auth_headers
        )
    assert resp.status == 400


async def test_recycle_revert_supernote_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_FS}.revert_from_recycle", new_callable=AsyncMock) as m:
        m.side_effect = SupernoteError("error")
        resp = await client.post(
            "/api/file/recycle/revert", json={"idList": []}, headers=auth_headers
        )
    assert resp.status == 400


async def test_recycle_clear_supernote_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_FS}.clear_recycle", new_callable=AsyncMock) as m:
        m.side_effect = SupernoteError("error")
        resp = await client.post(
            "/api/file/recycle/clear", json={}, headers=auth_headers
        )
    assert resp.status == 400


async def test_path_query_supernote_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_FS}.get_path_info", new_callable=AsyncMock) as m:
        m.side_effect = SupernoteError("not found", status_code=404)
        resp = await client.post(
            "/api/file/path/query",
            json={"id": 1},
            headers=auth_headers,
        )
    assert resp.status == 404


async def test_path_query_generic_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_FS}.get_path_info", new_callable=AsyncMock) as m:
        m.side_effect = RuntimeError("boom")
        resp = await client.post(
            "/api/file/path/query",
            json={"id": 1},
            headers=auth_headers,
        )
    assert resp.status == 500


async def test_file_list_query_supernote_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_FS}.query_file_list", new_callable=AsyncMock) as m:
        m.side_effect = SupernoteError("error")
        resp = await client.post(
            "/api/file/list/query",
            json={"directoryId": 0, "pageNo": 1, "pageSize": 10},
            headers=auth_headers,
        )
    assert resp.status == 400


async def test_file_list_query_generic_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_FS}.query_file_list", new_callable=AsyncMock) as m:
        m.side_effect = RuntimeError("boom")
        resp = await client.post(
            "/api/file/list/query",
            json={"directoryId": 0, "pageNo": 1, "pageSize": 10},
            headers=auth_headers,
        )
    assert resp.status == 500


async def test_file_search_supernote_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_FS}.search_files", new_callable=AsyncMock) as m:
        m.side_effect = SupernoteError("error")
        resp = await client.post(
            "/api/file/label/list/search",
            json={"keyword": "test"},
            headers=auth_headers,
        )
    assert resp.status == 400


async def test_file_search_generic_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_FS}.search_files", new_callable=AsyncMock) as m:
        m.side_effect = RuntimeError("boom")
        resp = await client.post(
            "/api/file/label/list/search",
            json={"keyword": "test"},
            headers=auth_headers,
        )
    assert resp.status == 500


async def test_folder_add_supernote_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_FS}.create_directory_by_id", new_callable=AsyncMock) as m:
        m.side_effect = SupernoteError("already exists", status_code=409)
        resp = await client.post(
            "/api/file/folder/add",
            json={"directoryId": 0, "fileName": "mydir"},
            headers=auth_headers,
        )
    assert resp.status == 409


async def test_folder_add_generic_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_FS}.create_directory_by_id", new_callable=AsyncMock) as m:
        m.side_effect = RuntimeError("boom")
        resp = await client.post(
            "/api/file/folder/add",
            json={"directoryId": 0, "fileName": "mydir"},
            headers=auth_headers,
        )
    assert resp.status == 500


async def test_folder_list_query_supernote_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_FS}.get_folders_by_ids", new_callable=AsyncMock) as m:
        m.side_effect = SupernoteError("error")
        resp = await client.post(
            "/api/file/folder/list/query",
            json={"directoryId": 0, "idList": []},
            headers=auth_headers,
        )
    assert resp.status == 400


async def test_folder_list_query_generic_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_FS}.get_folders_by_ids", new_callable=AsyncMock) as m:
        m.side_effect = RuntimeError("boom")
        resp = await client.post(
            "/api/file/folder/list/query",
            json={"directoryId": 0, "idList": []},
            headers=auth_headers,
        )
    assert resp.status == 500


async def test_file_delete_supernote_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_FS}.delete_items", new_callable=AsyncMock) as m:
        m.side_effect = SupernoteError("not found", status_code=404)
        resp = await client.post(
            "/api/file/delete",
            json={"idList": [99], "directoryId": 0},
            headers=auth_headers,
        )
    assert resp.status == 404


async def test_file_delete_generic_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_FS}.delete_items", new_callable=AsyncMock) as m:
        m.side_effect = RuntimeError("boom")
        resp = await client.post(
            "/api/file/delete",
            json={"idList": [99], "directoryId": 0},
            headers=auth_headers,
        )
    assert resp.status == 500


async def test_upload_finish_supernote_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_FS}.upload_finish_web", new_callable=AsyncMock) as m:
        m.side_effect = SupernoteError("not found", status_code=404)
        resp = await client.post(
            "/api/file/upload/finish",
            json={
                "fileSize": 100,
                "fileName": "x.note",
                "md5": "abc",
                "innerName": "uuid.note",
            },
            headers=auth_headers,
        )
    assert resp.status == 404


async def test_upload_finish_generic_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(f"{_FS}.upload_finish_web", new_callable=AsyncMock) as m:
        m.side_effect = RuntimeError("boom")
        resp = await client.post(
            "/api/file/upload/finish",
            json={
                "fileSize": 100,
                "fileName": "x.note",
                "md5": "abc",
                "innerName": "uuid.note",
            },
            headers=auth_headers,
        )
    assert resp.status == 500
