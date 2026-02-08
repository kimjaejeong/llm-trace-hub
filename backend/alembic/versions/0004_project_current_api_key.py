"""add current_api_key to projects

Revision ID: 0004_project_current_api_key
Revises: 0003_project_key_activated
Create Date: 2026-02-08
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_project_current_api_key"
down_revision = "0003_project_key_activated"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("current_api_key", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "current_api_key")
