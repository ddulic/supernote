"""add prompt_config table and prompt_hash column

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-17 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "f_prompt_config",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("layer", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("create_time", sa.BigInteger(), nullable=False),
        sa.Column("update_time", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "category", "layer", name="uq_prompt_config"),
    )
    op.create_index("ix_f_prompt_config_user_id", "f_prompt_config", ["user_id"])
    op.add_column(
        "f_note_page_content",
        sa.Column("prompt_hash", sa.String(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("f_note_page_content", "prompt_hash")
    op.drop_index("ix_f_prompt_config_user_id", table_name="f_prompt_config")
    op.drop_table("f_prompt_config")
