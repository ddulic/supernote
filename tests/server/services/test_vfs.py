from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from supernote.server.db.models.file import RecycleFileDO
from supernote.server.services.vfs import VirtualFileSystem


async def test_vfs_directory_operations(db_session: AsyncSession) -> None:
    vfs = VirtualFileSystem(db_session)
    user_id = 999
    root_id = 0

    # Create Directory
    folder = await vfs.create_directory(user_id, root_id, "MyFolder")
    assert folder.id > 0
    assert folder.file_name == "MyFolder"
    assert folder.directory_id == root_id

    # Helper to check listing
    children = await vfs.list_directory(user_id, root_id)
    assert len(children) == 1
    assert children[0].id == folder.id

    # Create sub-directory
    subfolder = await vfs.create_directory(user_id, folder.id, "SubFolder")
    assert subfolder.directory_id == folder.id

    # List sub-directory
    sub_children = await vfs.list_directory(user_id, folder.id)
    assert len(sub_children) == 1
    assert sub_children[0].file_name == "SubFolder"


async def test_vfs_file_operations(db_session: AsyncSession) -> None:
    vfs = VirtualFileSystem(db_session)
    user_id = 888

    # Create File
    file_node = await vfs.create_file(
        user_id, 0, "test.txt", size=100, md5="hash", storage_key="test-key"
    )
    assert file_node.file_name == "test.txt"
    assert file_node.is_folder == "N"

    # Verify in list
    children = await vfs.list_directory(user_id, 0)
    assert len(children) == 1
    assert children[0].md5 == "hash"

    # Soft Delete
    deleted = await vfs.delete_node(user_id, file_node.id)
    assert deleted is True

    # Verify gone from list
    children = await vfs.list_directory(user_id, 0)
    assert len(children) == 0

    # Verify can't get
    node = await vfs.get_node_by_id(user_id, file_node.id)
    assert node is None


async def test_delete_node_folder_recursive_soft_deletes_all_children(
    db_session: AsyncSession,
) -> None:
    """T027: delete_node on a folder must recursively soft-delete all active
    descendants and create RecycleFileDO entries for each file node."""
    vfs = VirtualFileSystem(db_session)
    user_id = 777

    # Build: root_folder → sub_folder → file1.note, file2.note
    root_folder = await vfs.create_directory(user_id, 0, "root_folder")
    sub_folder = await vfs.create_directory(user_id, root_folder.id, "sub_folder")
    file1 = await vfs.create_file(
        user_id,
        sub_folder.id,
        "file1.note",
        size=100,
        md5="md5_file1",
        storage_key="key_file1",
    )
    file2 = await vfs.create_file(
        user_id,
        sub_folder.id,
        "file2.note",
        size=200,
        md5="md5_file2",
        storage_key="key_file2",
    )

    # Delete the root folder
    result = await vfs.delete_node(user_id, root_folder.id)
    assert result is True

    # Expire cached state so we read fresh values from DB
    await db_session.refresh(root_folder)
    await db_session.refresh(sub_folder)
    await db_session.refresh(file1)
    await db_session.refresh(file2)

    # root_folder must be soft-deleted
    assert root_folder.is_active == "N", "root_folder should be soft-deleted"

    # sub_folder must ALSO be soft-deleted (this is the bug being fixed)
    assert sub_folder.is_active == "N", "sub_folder should be recursively soft-deleted"

    # Both files must be soft-deleted
    assert file1.is_active == "N", "file1.note should be recursively soft-deleted"
    assert file2.is_active == "N", "file2.note should be recursively soft-deleted"

    # RecycleFileDO entries must exist for each file node (not folders per current semantics)
    recycle_result = await db_session.execute(
        select(RecycleFileDO).where(RecycleFileDO.user_id == user_id)
    )
    recycle_entries = list(recycle_result.scalars().all())
    recycled_file_ids = {entry.file_id for entry in recycle_entries}

    assert file1.id in recycled_file_ids, "file1 should have a RecycleFileDO entry"
    assert file2.id in recycled_file_ids, "file2 should have a RecycleFileDO entry"


async def test_copy_node_folder_deep_copies_nested_structure(
    db_session: AsyncSession,
) -> None:
    """T028: copy_node on a folder must produce a complete deep copy of the
    folder hierarchy under the target parent, preserving names and storage keys."""
    vfs = VirtualFileSystem(db_session)
    user_id = 666

    # Build source: source_folder → sub_folder → file1.note
    source_folder = await vfs.create_directory(user_id, 0, "source_folder")
    sub_folder = await vfs.create_directory(user_id, source_folder.id, "sub_folder")
    original_file = await vfs.create_file(
        user_id,
        sub_folder.id,
        "file1.note",
        size=512,
        md5="original_md5",
        storage_key="original_storage_key",
    )

    # Create an independent target destination
    target_folder = await vfs.create_directory(user_id, 0, "target_folder")

    # Copy source_folder into target_folder
    copied_root = await vfs.copy_node(
        user_id=user_id,
        source_node_id=source_folder.id,
        new_parent_id=target_folder.id,
        autorename=False,
        new_name="source_folder",
    )

    assert copied_root is not None, "copy_node should return the new root node"
    assert copied_root.file_name == "source_folder"
    assert copied_root.directory_id == target_folder.id
    assert copied_root.id != source_folder.id, "copy must have a distinct ID"

    # target_folder should now contain the copy of source_folder
    target_children = await vfs.list_directory(user_id, target_folder.id)
    assert len(target_children) == 1
    assert target_children[0].file_name == "source_folder"

    # The copy should contain sub_folder
    copy_children = await vfs.list_directory(user_id, copied_root.id)
    assert len(copy_children) == 1
    copied_sub_folder = copy_children[0]
    assert copied_sub_folder.file_name == "sub_folder"
    assert copied_sub_folder.id != sub_folder.id, "copied sub_folder must have a new ID"

    # The copied sub_folder should contain file1.note
    copied_sub_children = await vfs.list_directory(user_id, copied_sub_folder.id)
    assert len(copied_sub_children) == 1
    copied_file = copied_sub_children[0]
    assert copied_file.file_name == "file1.note"
    assert copied_file.id != original_file.id, "copied file must have a new ID"

    # Copied file must share the same storage_key (CAS / content-addressable storage)
    assert copied_file.storage_key == original_file.storage_key, (
        "copied file should reference the same storage_key as the original"
    )

    # Original source folder must remain untouched and active
    await db_session.refresh(source_folder)
    await db_session.refresh(sub_folder)
    await db_session.refresh(original_file)

    assert source_folder.is_active == "Y", (
        "original source_folder should still be active"
    )
    assert sub_folder.is_active == "Y", "original sub_folder should still be active"
    assert original_file.is_active == "Y", "original file should still be active"
