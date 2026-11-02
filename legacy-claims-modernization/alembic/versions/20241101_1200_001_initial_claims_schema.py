"""Initial claims schema

Revision ID: 001
Revises: 
Create Date: 2024-11-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create claim_type enum
    claim_type_enum = postgresql.ENUM(
        'ACCIDENT', 'THEFT', 'PROPERTY_DAMAGE', 'LIABILITY', 'MEDICAL', 'OTHER',
        name='claim_type_enum', create_type=False
    )
    claim_type_enum.create(op.get_bind())
    
    # Create claim_status enum
    claim_status_enum = postgresql.ENUM(
        'SUBMITTED', 'UNDER_REVIEW', 'APPROVED', 'REJECTED', 'PAID', 'CLOSED',
        name='claim_status_enum', create_type=False
    )
    claim_status_enum.create(op.get_bind())
    
    # Create claims table
    op.create_table(
        'claims',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('policy_reference', sa.String(length=50), nullable=False),
        sa.Column('claim_type', claim_type_enum, nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('claimed_amount', sa.DECIMAL(precision=12, scale=2), nullable=False),
        sa.Column('status', claim_status_enum, nullable=False, server_default='SUBMITTED'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('claimed_amount >= 0', name='claimed_amount_non_negative'),
        sa.CheckConstraint('version >= 1', name='version_positive'),
        sa.CheckConstraint('length(description) <= 2000', name='description_max_length'),
        sa.CheckConstraint('length(policy_reference) >= 1', name='policy_reference_not_empty'),
    )
    
    # Create indexes
    op.create_index('ix_claims_policy_reference', 'claims', ['policy_reference'])
    op.create_index('ix_claims_status', 'claims', ['status'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_claims_status', table_name='claims')
    op.drop_index('ix_claims_policy_reference', table_name='claims')
    
    # Drop table
    op.drop_table('claims')
    
    # Drop enums
    op.execute('DROP TYPE claim_status_enum')
    op.execute('DROP TYPE claim_type_enum')
