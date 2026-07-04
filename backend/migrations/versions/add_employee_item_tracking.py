"""Add employee and item tracking for departments

Revision ID: add_employee_item_tracking
Revises: add_warehouse_hierarchy
Create Date: 2026-07-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_employee_item_tracking'
down_revision = 'add_warehouse_hierarchy'
branch_labels = None
depends_on = None


def upgrade():
    # Add warehouse_id to departments table
    op.add_column('departments', sa.Column('warehouse_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_departments_warehouse_id', 'departments', 'warehouses', ['warehouse_id'], ['id'])
    op.create_index('ix_departments_warehouse_id', 'departments', ['warehouse_id'])

    # Create employees table
    op.create_table(
        'employees',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organisation_id', sa.Integer(), nullable=False),
        sa.Column('department_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('date_of_join', sa.DateTime(), nullable=False),
        sa.Column('employee_type', sa.String(50), default='regular', nullable=False),
        sa.Column('manager_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organisation_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
        sa.ForeignKeyConstraint(['manager_id'], ['employees.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organisation_id', 'code', name='uq_employee_org_code')
    )
    op.create_index('ix_employees_org_id', 'employees', ['organisation_id'])
    op.create_index('ix_employees_department_id', 'employees', ['department_id'])
    op.create_index('ix_employees_code', 'employees', ['code'])
    op.create_index('ix_employees_active', 'employees', ['is_active'])

    # Create item_issues table
    op.create_table(
        'item_issues',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organisation_id', sa.Integer(), nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.Column('from_warehouse_id', sa.Integer(), nullable=False),
        sa.Column('to_department_id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('reference', sa.String(100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('issued_by', sa.Integer(), nullable=False),
        sa.Column('issued_date', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organisation_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['item_id'], ['inventory_items.id'], ),
        sa.ForeignKeyConstraint(['from_warehouse_id'], ['warehouses.id'], ),
        sa.ForeignKeyConstraint(['to_department_id'], ['departments.id'], ),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ),
        sa.ForeignKeyConstraint(['issued_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_item_issues_org_id', 'item_issues', ['organisation_id'])
    op.create_index('ix_item_issues_item_id', 'item_issues', ['item_id'])
    op.create_index('ix_item_issues_warehouse_id', 'item_issues', ['from_warehouse_id'])
    op.create_index('ix_item_issues_department_id', 'item_issues', ['to_department_id'])
    op.create_index('ix_item_issues_employee_id', 'item_issues', ['employee_id'])
    op.create_index('ix_item_issues_issued_date', 'item_issues', ['issued_date'])

    # Create item_returns table
    op.create_table(
        'item_returns',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organisation_id', sa.Integer(), nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.Column('from_department_id', sa.Integer(), nullable=False),
        sa.Column('to_warehouse_id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('condition', sa.String(50), default='good', nullable=False),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('reference', sa.String(100), nullable=True),
        sa.Column('returned_by', sa.Integer(), nullable=False),
        sa.Column('return_date', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organisation_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['item_id'], ['inventory_items.id'], ),
        sa.ForeignKeyConstraint(['from_department_id'], ['departments.id'], ),
        sa.ForeignKeyConstraint(['to_warehouse_id'], ['warehouses.id'], ),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ),
        sa.ForeignKeyConstraint(['returned_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_item_returns_org_id', 'item_returns', ['organisation_id'])
    op.create_index('ix_item_returns_item_id', 'item_returns', ['item_id'])
    op.create_index('ix_item_returns_department_id', 'item_returns', ['from_department_id'])
    op.create_index('ix_item_returns_warehouse_id', 'item_returns', ['to_warehouse_id'])
    op.create_index('ix_item_returns_employee_id', 'item_returns', ['employee_id'])
    op.create_index('ix_item_returns_return_date', 'item_returns', ['return_date'])


def downgrade():
    # Drop item_returns table
    op.drop_index('ix_item_returns_return_date', table_name='item_returns')
    op.drop_index('ix_item_returns_employee_id', table_name='item_returns')
    op.drop_index('ix_item_returns_warehouse_id', table_name='item_returns')
    op.drop_index('ix_item_returns_department_id', table_name='item_returns')
    op.drop_index('ix_item_returns_item_id', table_name='item_returns')
    op.drop_index('ix_item_returns_org_id', table_name='item_returns')
    op.drop_table('item_returns')

    # Drop item_issues table
    op.drop_index('ix_item_issues_issued_date', table_name='item_issues')
    op.drop_index('ix_item_issues_employee_id', table_name='item_issues')
    op.drop_index('ix_item_issues_department_id', table_name='item_issues')
    op.drop_index('ix_item_issues_warehouse_id', table_name='item_issues')
    op.drop_index('ix_item_issues_item_id', table_name='item_issues')
    op.drop_index('ix_item_issues_org_id', table_name='item_issues')
    op.drop_table('item_issues')

    # Drop employees table
    op.drop_index('ix_employees_active', table_name='employees')
    op.drop_index('ix_employees_code', table_name='employees')
    op.drop_index('ix_employees_department_id', table_name='employees')
    op.drop_index('ix_employees_org_id', table_name='employees')
    op.drop_table('employees')

    # Drop warehouse_id from departments table
    op.drop_index('ix_departments_warehouse_id', table_name='departments')
    op.drop_constraint('fk_departments_warehouse_id', 'departments', type_='foreignkey')
    op.drop_column('departments', 'warehouse_id')
