"""add is_active to projects

Revision ID: 0002_project_active
Revises: 0001_init
Create Date: 2026-02-08
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0002_project_active"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.execute("UPDATE projects SET is_active = TRUE")


def downgrade() -> None:
    op.drop_column("projects", "is_active")
