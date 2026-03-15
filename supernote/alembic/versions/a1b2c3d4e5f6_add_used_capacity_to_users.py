"""add used_capacity to users

Revision ID: a1b2c3d4e5f6
Revises: 0543a383957b
Create Date: 2026-03-15 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "0543a383957b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column("used_capacity", sa.Integer(), nullable=False, server_default="0"),
    )
    # Reconciliation: set used_capacity from existing active file sizes
    op.execute(
        "UPDATE users SET used_capacity = COALESCE("
        "(SELECT SUM(f.size) FROM f_user_file f "
        "WHERE f.user_id = users.id AND f.is_active = 'Y' AND f.is_folder = 'N'), 0)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "used_capacity")
