"""Create audit_entries table

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-07
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_entries",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("entry_id", sa.Text(), nullable=False, unique=True),
        sa.Column("timestamp", sa.Text(), nullable=False),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("resource", sa.Text(), nullable=False),
        sa.Column("metadata", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("previous_hash", sa.Text(), nullable=False),
        sa.Column("entry_hash", sa.Text(), nullable=False),
    )
    # Append order matters for chain verification (list_entries orders by
    # this), and every append reads "the last row" — an index keeps that
    # cheap as the table grows.
    op.create_index("ix_audit_entries_id", "audit_entries", ["id"])


def downgrade() -> None:
    op.drop_index("ix_audit_entries_id", table_name="audit_entries")
    op.drop_table("audit_entries")
