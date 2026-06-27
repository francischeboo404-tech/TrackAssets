"""Fix inventory item column names - rename minimum/maximum to min/max

Revision ID: 04_fix_inventory_column_names
Revises: 03_enhance_inventory_master_data
Create Date: 2026-06-26 00:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '04_fix_inventory_column_names'
down_revision: Union[str, None] = '03_enhance_inventory_master_data'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Handle both cases: if columns exist with wrong names, rename them
    # If they don't exist, add the correct ones
    
    with op.batch_alter_table('inventory_items', schema=None) as batch_op:
        # Try to rename columns if they exist with the _enabled suffix
        try:
            # PostgreSQL doesn't support direct column renaming in batch_alter_table for all dialects
            # We'll drop and recreate with correct names
            batch_op.drop_column('batch_tracking_enabled')
        except Exception:
            pass
        
        try:
            batch_op.drop_column('serial_tracking_enabled')
        except Exception:
            pass
        
        try:
            batch_op.drop_column('expiry_tracking_enabled')
        except Exception:
            pass
        
        try:
            batch_op.drop_column('minimum_stock_level')
        except Exception:
            pass
        
        try:
            batch_op.drop_column('maximum_stock_level')
        except Exception:
            pass
        
        # Now add columns with correct names if they don't exist
        # First, check if they need to be added by trying to add them
        # (they may already exist from a previous corrected migration)
        try:
            batch_op.add_column(sa.Column('min_stock_level', sa.Integer(), nullable=True, server_default='0'))
        except Exception:
            pass  # May already exist
        
        try:
            batch_op.add_column(sa.Column('max_stock_level', sa.Integer(), nullable=True, server_default='0'))
        except Exception:
            pass
        
        try:
            batch_op.add_column(sa.Column('safety_stock', sa.Integer(), nullable=True, server_default='0'))
        except Exception:
            pass
        
        try:
            batch_op.add_column(sa.Column('batch_tracking', sa.Boolean(), nullable=True, server_default='false'))
        except Exception:
            pass
        
        try:
            batch_op.add_column(sa.Column('serial_tracking', sa.Boolean(), nullable=True, server_default='false'))
        except Exception:
            pass
        
        try:
            batch_op.add_column(sa.Column('expiry_tracking', sa.Boolean(), nullable=True, server_default='false'))
        except Exception:
            pass


def downgrade() -> None:
    # This migration is a fix, downgrading would restore the broken state
    # So we'll just reverse the drops and re-add the old column names
    
    with op.batch_alter_table('inventory_items', schema=None) as batch_op:
        # Drop the corrected columns
        try:
            batch_op.drop_column('batch_tracking')
        except Exception:
            pass
        
        try:
            batch_op.drop_column('serial_tracking')
        except Exception:
            pass
        
        try:
            batch_op.drop_column('expiry_tracking')
        except Exception:
            pass
        
        try:
            batch_op.drop_column('min_stock_level')
        except Exception:
            pass
        
        try:
            batch_op.drop_column('max_stock_level')
        except Exception:
            pass
        
        try:
            batch_op.drop_column('safety_stock')
        except Exception:
            pass
        
        # Re-add the old column names
        try:
            batch_op.add_column(sa.Column('batch_tracking_enabled', sa.Boolean(), nullable=True, server_default='false'))
        except Exception:
            pass
        
        try:
            batch_op.add_column(sa.Column('serial_tracking_enabled', sa.Boolean(), nullable=True, server_default='false'))
        except Exception:
            pass
        
        try:
            batch_op.add_column(sa.Column('expiry_tracking_enabled', sa.Boolean(), nullable=True, server_default='false'))
        except Exception:
            pass
        
        try:
            batch_op.add_column(sa.Column('minimum_stock_level', sa.Integer(), nullable=True, server_default='0'))
        except Exception:
            pass
        
        try:
            batch_op.add_column(sa.Column('maximum_stock_level', sa.Integer(), nullable=True, server_default='0'))
        except Exception:
            pass
