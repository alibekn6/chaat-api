"""Add ondelete CASCADE to email_verifications.user_id

Revision ID: f2b1e9907336
Revises: fead8f0cead7
Create Date: 2025-07-17 11:27:46.009063

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2b1e9907336'
down_revision: Union[str, None] = 'fead8f0cead7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('email_verifications_user_id_fkey', 'email_verifications', type_='foreignkey')
    op.create_foreign_key(
        'email_verifications_user_id_fkey',
        'email_verifications', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE'
    )

def downgrade() -> None:
    op.drop_constraint('email_verifications_user_id_fkey', 'email_verifications', type_='foreignkey')
    op.create_foreign_key(
        'email_verifications_user_id_fkey',
        'email_verifications', 'users',
        ['user_id'], ['id'],
        ondelete=None
    )
