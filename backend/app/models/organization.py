from datetime import datetime

from app import db


class Organization(db.Model):
    """Multi-tenant organization model"""

    __tablename__ = "organizations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    code = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.Text)
    logo_url = db.Column(db.String(512), nullable=True)
    preferences = db.Column(db.JSON, default={})
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    users = db.relationship("User", backref="organization", lazy=True)
    departments = db.relationship(
        "Department",
        backref="organization",
        lazy=True,
        cascade="all, delete-orphan",
    )
    assets = db.relationship(
        "Asset",
        backref="organization",
        lazy=True,
        cascade="all, delete-orphan",
    )
    inventory_items = db.relationship(
        "InventoryItem",
        backref="organization",
        lazy=True,
        cascade="all, delete-orphan",
    )
    audit_logs = db.relationship(
        "AuditLog",
        backref="organization",
        lazy=True,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.Index("ix_organizations_code", "code"),
        db.Index("ix_organizations_active", "is_active"),
    )

    def __repr__(self):
        return f"<Organization {self.code}>"


class Department(db.Model):
    """Department model for organizing assets and inventory within a warehouse"""

    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True)
    organisation_id = db.Column(
        db.Integer, db.ForeignKey("organizations.id"), nullable=False
    )
    warehouse_id = db.Column(
        db.Integer, db.ForeignKey("warehouses.id"), nullable=True
    )
    name = db.Column(db.String(255), nullable=False)
    code = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    head_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    allowed_category_ids = db.Column(db.JSON, default=list)
    allowed_inventory_item_types = db.Column(db.JSON, default=list)
    allowed_asset_types = db.Column(db.JSON, default=list)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        db.UniqueConstraint(
            "organisation_id", "code", name="uq_dept_org_code"
        ),
        db.Index("ix_departments_org_id", "organisation_id"),
        db.Index("ix_departments_warehouse_id", "warehouse_id"),
        db.Index("ix_departments_head_id", "head_id"),
        db.Index("ix_departments_active", "is_active"),
    )

    assets = db.relationship(
        "Asset",
        foreign_keys="[Asset.department_id]",
        backref="department",
        lazy=True,
    )
    head = db.relationship(
        "User", backref="headed_departments", foreign_keys=[head_id]
    )
    
    warehouse = db.relationship(
        "Warehouse",
        backref="departments",
        foreign_keys=[warehouse_id]
    )
    
    employees = db.relationship(
        "Employee",
        backref="department",
        lazy=True,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Department {self.code}>"


class Employee(db.Model):
    """Employee model for tracking employee details and item issuances"""

    __tablename__ = "employees"

    id = db.Column(db.Integer, primary_key=True)
    organisation_id = db.Column(
        db.Integer, db.ForeignKey("organizations.id"), nullable=False
    )
    department_id = db.Column(
        db.Integer, db.ForeignKey("departments.id"), nullable=False
    )
    name = db.Column(db.String(255), nullable=False)
    code = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(255))
    phone = db.Column(db.String(20))
    date_of_join = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    employee_type = db.Column(db.String(50), default="regular")  # regular|contract|temporary
    manager_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        db.UniqueConstraint(
            "organisation_id", "code", name="uq_employee_org_code"
        ),
        db.Index("ix_employees_org_id", "organisation_id"),
        db.Index("ix_employees_department_id", "department_id"),
        db.Index("ix_employees_code", "code"),
        db.Index("ix_employees_active", "is_active"),
    )

    issued_items = db.relationship(
        "ItemIssue",
        backref="employee",
        lazy=True,
        cascade="all, delete-orphan",
        foreign_keys="[ItemIssue.employee_id]"
    )

    returned_items = db.relationship(
        "ItemReturn",
        backref="employee",
        lazy=True,
        cascade="all, delete-orphan",
        foreign_keys="[ItemReturn.employee_id]"
    )

    manager = db.relationship(
        "Employee",
        remote_side=[id],
        backref="subordinates",
        foreign_keys=[manager_id]
    )

    def __repr__(self):
        return f"<Employee {self.code}>"


class ItemIssue(db.Model):
    """Item Issue model tracking when items are issued to employees in departments"""

    __tablename__ = "item_issues"

    id = db.Column(db.Integer, primary_key=True)
    organisation_id = db.Column(
        db.Integer, db.ForeignKey("organizations.id"), nullable=False
    )
    item_id = db.Column(
        db.Integer, db.ForeignKey("inventory_items.id"), nullable=False
    )
    from_warehouse_id = db.Column(
        db.Integer, db.ForeignKey("warehouses.id"), nullable=False
    )
    to_department_id = db.Column(
        db.Integer, db.ForeignKey("departments.id"), nullable=False
    )
    employee_id = db.Column(
        db.Integer, db.ForeignKey("employees.id"), nullable=False
    )
    quantity = db.Column(db.Integer, nullable=False)
    reference = db.Column(db.String(100))
    notes = db.Column(db.Text)
    issued_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    issued_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        db.Index("ix_item_issues_org_id", "organisation_id"),
        db.Index("ix_item_issues_item_id", "item_id"),
        db.Index("ix_item_issues_warehouse_id", "from_warehouse_id"),
        db.Index("ix_item_issues_department_id", "to_department_id"),
        db.Index("ix_item_issues_employee_id", "employee_id"),
        db.Index("ix_item_issues_issued_date", "issued_date"),
    )

    item = db.relationship(
        "InventoryItem",
        backref="issues",
        foreign_keys=[item_id]
    )

    from_warehouse = db.relationship(
        "Warehouse",
        backref="issued_items",
        foreign_keys=[from_warehouse_id]
    )

    to_department = db.relationship(
        "Department",
        backref="issued_items",
        foreign_keys=[to_department_id]
    )

    issued_by_user = db.relationship(
        "User",
        backref="issued_items",
        foreign_keys=[issued_by]
    )

    def __repr__(self):
        return f"<ItemIssue {self.id}>"


class ItemReturn(db.Model):
    """Item Return model tracking when employees return items to warehouses"""

    __tablename__ = "item_returns"

    id = db.Column(db.Integer, primary_key=True)
    organisation_id = db.Column(
        db.Integer, db.ForeignKey("organizations.id"), nullable=False
    )
    item_id = db.Column(
        db.Integer, db.ForeignKey("inventory_items.id"), nullable=False
    )
    from_department_id = db.Column(
        db.Integer, db.ForeignKey("departments.id"), nullable=False
    )
    to_warehouse_id = db.Column(
        db.Integer, db.ForeignKey("warehouses.id"), nullable=False
    )
    employee_id = db.Column(
        db.Integer, db.ForeignKey("employees.id"), nullable=False
    )
    quantity = db.Column(db.Integer, nullable=False)
    condition = db.Column(
        db.String(50),
        default="good",
        nullable=False
    )  # good|damaged|worn|partial
    remarks = db.Column(db.Text)
    reference = db.Column(db.String(100))
    returned_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    return_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        db.Index("ix_item_returns_org_id", "organisation_id"),
        db.Index("ix_item_returns_item_id", "item_id"),
        db.Index("ix_item_returns_department_id", "from_department_id"),
        db.Index("ix_item_returns_warehouse_id", "to_warehouse_id"),
        db.Index("ix_item_returns_employee_id", "employee_id"),
        db.Index("ix_item_returns_return_date", "return_date"),
    )

    item = db.relationship(
        "InventoryItem",
        backref="returns",
        foreign_keys=[item_id]
    )

    from_department = db.relationship(
        "Department",
        backref="returned_items",
        foreign_keys=[from_department_id]
    )

    to_warehouse = db.relationship(
        "Warehouse",
        backref="returned_items",
        foreign_keys=[to_warehouse_id]
    )

    returned_by_user = db.relationship(
        "User",
        backref="returned_items",
        foreign_keys=[returned_by]
    )

    def __repr__(self):
        return f"<ItemReturn {self.id}>"
