"""add frame_timings table

Revision ID: c7f1a4d9b2e3
Revises: 6e55088f8611
Create Date: 2026-09-28 11:05:00.000000

frame_timings backs the per-frame detection timings used by the FPS strip.
It was present in the ORM (app/models/frame_timing.py) and was created in
running deployments by the metadata-based init_models() path, but had no
migration, so `alembic upgrade head` produced a schema missing the table
entirely. Adding it as an explicit create_table migration is safe for
existing deployments: the table is only created if absent, and the one
migrated below already carries it.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7f1a4d9b2e3"
down_revision: str | None = "6e55088f8611"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "frame_timings" in inspector.get_table_names():
        # Already present (created by init_models() on a pre-migration
        # deployment). Adopting it as-is rather than failing or recreating,
        # which would discard recorded timings.
        return

    op.create_table(
        "frame_timings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("video_id", sa.String(length=36), nullable=False),
        sa.Column("frame_id", sa.Integer(), nullable=False),
        sa.Column("elapsed_ms", sa.Float(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["video_id"],
            ["videos.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("frame_timings", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_frame_timings_video_id"), ["video_id"], unique=False)


def downgrade() -> None:
    op.drop_table("frame_timings")
