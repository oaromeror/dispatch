"""Add CF fields

Revision ID: 25bcc0ec3426
Revises: 78bdaae1224g
Create Date: 2023-07-24 16:39:54.636974

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '25bcc0ec3426'
down_revision = '78bdaae1224g'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('incident', sa.Column('cf', sa.Boolean(), nullable=True, default=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('incident', 'cf')
    # ### end Alembic commands ###
