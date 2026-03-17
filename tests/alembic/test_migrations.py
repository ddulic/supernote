"""Tests for Alembic migration scripts."""

from unittest.mock import patch

import supernote.alembic.versions.a1b2c3d4e5f6_add_used_capacity_to_users as migration
import supernote.alembic.versions.c3d4e5f6a7b8_add_last_conversion_md5_to_user_file as migration_md5


def test_downgrade_drops_used_capacity_column() -> None:
    """downgrade() calls op.drop_column to remove the used_capacity column."""
    with patch.object(migration, "op") as mock_op:
        migration.downgrade()
    mock_op.drop_column.assert_called_once_with("users", "used_capacity")


def test_downgrade_drops_last_conversion_md5_column() -> None:
    """downgrade() calls op.drop_column to remove the last_conversion_md5 column."""
    with patch.object(migration_md5, "op") as mock_op:
        migration_md5.downgrade()
    mock_op.drop_column.assert_called_once_with("f_user_file", "last_conversion_md5")
