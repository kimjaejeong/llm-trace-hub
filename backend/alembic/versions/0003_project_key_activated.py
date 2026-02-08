"""add key_activated to projects

Revision ID: 0003_project_key_activated
Revises: 0002_project_active
Create Date: 2026-02-08
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_project_key_activated"
down_revision = "0002_project_active"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("key_activated", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.execute("UPDATE projects SET key_activated = FALSE")


def downgrade() -> None:
    op.drop_column("projects", "key_activated")
