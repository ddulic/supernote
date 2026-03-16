"""Tests for Alembic migration scripts."""

from unittest.mock import patch

import supernote.alembic.versions.a1b2c3d4e5f6_add_used_capacity_to_users as migration


def test_downgrade_drops_used_capacity_column() -> None:
    """downgrade() calls op.drop_column to remove the used_capacity column."""
    with patch.object(migration, "op") as mock_op:
        migration.downgrade()
    mock_op.drop_column.assert_called_once_with("users", "used_capacity")
