import time

from sqlalchemy import BigInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from supernote.server.db.base import Base
from supernote.server.utils.unique_id import next_id


class PromptConfigDO(Base):
    """Per-user prompt configuration overrides."""

    __tablename__ = "f_prompt_config"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, default=next_id)
    """Internal database ID."""

    user_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    """The numeric ID of the user who owns this config."""

    category: Mapped[str] = mapped_column(String, nullable=False)
    """Prompt category: 'ocr' or 'summary'."""

    layer: Mapped[str] = mapped_column(String, nullable=False)
    """Prompt layer: 'common', 'default', or a user-defined type name."""

    content: Mapped[str] = mapped_column(Text, nullable=False)
    """Full prompt text for this layer."""

    create_time: Mapped[int] = mapped_column(
        BigInteger, default=lambda: int(time.time() * 1000)
    )
    """System creation timestamp."""

    update_time: Mapped[int] = mapped_column(
        BigInteger,
        default=lambda: int(time.time() * 1000),
        onupdate=lambda: int(time.time() * 1000),
    )
    """System update timestamp."""

    __table_args__ = (
        UniqueConstraint("user_id", "category", "layer", name="uq_prompt_config"),
    )
