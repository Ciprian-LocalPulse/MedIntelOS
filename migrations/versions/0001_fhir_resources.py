"""Create fhir_resources table

Revision ID: 0001
Revises:
Create Date: 2026-09-07
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fhir_resources",
        sa.Column("resource_type", sa.Text(), nullable=False),
        sa.Column("resource_id", sa.Text(), nullable=False),
        sa.Column("version_id", sa.Integer(), nullable=False),
        sa.Column("document", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("resource_type", "resource_id", name="pk_fhir_resources"),
    )
    # Supports the API's fhir.search route: fetch-by-type is the only query
    # PostgresFHIRStore issues today (see fhir/postgres_repository.py's
    # documented boundary — filtering beyond resource_type happens in Python,
    # not SQL, as of 0.3.0).
    op.create_index(
        "ix_fhir_resources_resource_type",
        "fhir_resources",
        ["resource_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_fhir_resources_resource_type", table_name="fhir_resources")
    op.drop_table("fhir_resources")
