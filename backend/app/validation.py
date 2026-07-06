import re

from marshmallow import EXCLUDE, Schema, ValidationError, fields, pre_load, validate, validates_schema


class UserRegistrationSchema(Schema):
    username = fields.Str(
        required=True,
        validate=[
            validate.Length(min=3, max=120),
            validate.Regexp(
                r"^[a-zA-Z0-9_]+$",
                error="Username must contain only letters, numbers, and underscores",
            ),
        ],
    )
    email = fields.Email(required=True)
    password = fields.Str(
        required=True, validate=validate.Length(min=8, max=255)
    )
    first_name = fields.Str(validate=validate.Length(max=120))
    last_name = fields.Str(validate=validate.Length(max=120))
    phone_number = fields.Str(validate=validate.Length(max=20))
    department = fields.Str(validate=validate.Length(max=120))
    role = fields.Str(
        validate=validate.OneOf(
            [
                "admin",
                "staff",
                "viewer",
                "auditor",
                "dept_head",
                "store_manager",
            ]
        )
    )
    organisation_id = fields.Int(validate=validate.Range(min=1))

class OrganizationRegistrationSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    # Organization Info
    org_name = fields.Str(required=True, validate=validate.Length(min=2, max=255))
    org_code = fields.Str(
        required=True,
        validate=[
            validate.Length(min=2, max=50),
            validate.Regexp(
                r"^[A-Z0-9_]+$",
                error="Org code must be uppercase letters, numbers, and underscores",
            ),
        ],
    )
    org_description = fields.Str(
        required=False, allow_none=True, validate=validate.Length(max=1000)
    )

    # Admin Info
    admin_username = fields.Str(
        required=True,
        validate=[
            validate.Length(min=3, max=120),
            validate.Regexp(
                r"^[a-zA-Z0-9_]+$",
                error="Username must contain only letters, numbers, and underscores",
            ),
        ],
    )
    admin_email = fields.Email(required=True)
    admin_password = fields.Str(required=True, validate=validate.Length(min=8, max=255))
    admin_first_name = fields.Str(
        required=False, allow_none=True, validate=validate.Length(max=120)
    )
    admin_last_name = fields.Str(
        required=False, allow_none=True, validate=validate.Length(max=120)
    )

    @pre_load
    def normalize_org_code(self, data, **kwargs):
        if isinstance(data, dict) and data.get("org_code"):
            data = dict(data)
            code = str(data["org_code"]).strip().upper()
            code = re.sub(r"[^A-Z0-9]+", "_", code)
            data["org_code"] = re.sub(r"_+", "_", code).strip("_")
        return data


class UserLoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True)


class OrganizationSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    code = fields.Str(
        required=True,
        validate=[
            validate.Length(min=1, max=50),
            validate.Regexp(
                r"^[A-Z0-9_]+$",
                error="Code must be uppercase letters, numbers, and underscores",
            ),
        ],
    )
    description = fields.Str(validate=validate.Length(max=1000))


class DepartmentSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    code = fields.Str(
        required=True,
        validate=[
            validate.Length(min=1, max=50),
            validate.Regexp(
                r"^[A-Z0-9_]+$",
                error="Code must be uppercase letters, numbers, and underscores",
            ),
        ],
    )
    description = fields.Str(validate=validate.Length(max=1000))
    head_id = fields.Int(validate=validate.Range(min=1))
    allowed_category_ids = fields.List(
        fields.Int(validate=validate.Range(min=1)),
        load_default=[],
        allow_none=True,
    )
    allowed_inventory_item_types = fields.List(
        fields.Str(
            validate=validate.OneOf([
                "consumable",
                "asset",
                "raw",
                "finished",
                "service",
            ])
        ),
        load_default=[],
        allow_none=True,
    )
    allowed_asset_types = fields.List(
        fields.Str(validate=validate.Length(min=1, max=100)),
        load_default=[],
        allow_none=True,
    )
    warehouse_id = fields.Int(required=True, validate=validate.Range(min=1))


class DepartmentUpdateSchema(Schema):
    name = fields.Str(validate=validate.Length(min=1, max=255))
    code = fields.Str(
        validate=[
            validate.Length(min=1, max=50),
            validate.Regexp(
                r"^[A-Z0-9_]+$",
                error="Code must be uppercase letters, numbers, and underscores",
            ),
        ],
    )
    description = fields.Str(validate=validate.Length(max=1000), allow_none=True)
    head_id = fields.Int(validate=validate.Range(min=1), allow_none=True)
    allowed_category_ids = fields.List(
        fields.Int(validate=validate.Range(min=1)),
        allow_none=True,
    )
    allowed_inventory_item_types = fields.List(
        fields.Str(
            validate=validate.OneOf([
                "consumable",
                "asset",
                "raw",
                "finished",
                "service",
            ])
        ),
        allow_none=True,
    )
    allowed_asset_types = fields.List(
        fields.Str(validate=validate.Length(min=1, max=100)),
        allow_none=True,
    )
    warehouse_id = fields.Int(validate=validate.Range(min=1), allow_none=True)


class AssetSchema(Schema):
    # Allow asset_code to be optional so the service layer can auto-generate it
    asset_code = fields.Str(
        required=False,
        validate=[
            validate.Length(min=1, max=100),
            validate.Regexp(
                r"^[a-zA-Z0-9\-_./ ]+$",
                error="Asset code must contain only letters, numbers, hyphens, underscores, dots, slashes, and spaces",
            ),
        ],
    )
    name = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    type = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    serial_number = fields.Str(validate=validate.Length(max=255))
    department_id = fields.Int(required=True, validate=validate.Range(min=1))
    assigned_to = fields.Str(validate=validate.Length(max=255))
    location = fields.Str(validate=validate.Length(max=255))
    warehouse_id = fields.Int(validate=validate.Range(min=1))
    bin_id = fields.Int(validate=validate.Range(min=1))
    purchase_date = fields.Date(required=True)
    purchase_value = fields.Float(
        required=True, validate=validate.Range(min=0)
    )
    useful_life = fields.Int(
        required=True, validate=validate.Range(min=1, max=50)
    )
    qr_code_data = fields.Str(validate=validate.Length(max=500))


class AssetStatusUpdateSchema(Schema):
    status = fields.Str(
        required=True,
        validate=validate.OneOf(
            [
                "available",
                "assigned",
                "under_maintenance",
                "lost",
                "damaged",
                "disposed",
            ]
        ),
    )
    comments = fields.Str(validate=validate.Length(max=1000), allow_none=True)


class AssetAssignSchema(Schema):
    user_id = fields.Int(required=True, validate=validate.Range(min=1))
    department_id = fields.Int(required=True, validate=validate.Range(min=1))
    assignment_date = fields.Date(required=True)
    return_date = fields.Date(load_default=None, allow_none=True)


class ReturnAssetSchema(Schema):
    return_condition = fields.Str(
        required=True,
        validate=validate.OneOf(["good", "damaged", "lost"]),
    )
    actual_return_date = fields.Date(required=True)
    notes = fields.Str(validate=validate.Length(max=1000), allow_none=True)


class TransferRequestSchema(Schema):
    transfer_type = fields.Str(
        required=True,
        validate=validate.OneOf([
            "employee_to_employee",
            "department_to_department",
            "warehouse_to_warehouse",
        ]),
    )
    item_type = fields.Str(validate=validate.OneOf(["asset", "inventory"]), missing="asset")
    asset_id = fields.Int(validate=validate.Range(min=1), allow_none=True)
    inventory_item_id = fields.Int(validate=validate.Range(min=1), allow_none=True)
    quantity = fields.Int(validate=validate.Range(min=1), missing=1)
    # Required for department_to_department (and inventory transfers)
    new_department_id = fields.Int(validate=validate.Range(min=1), load_default=None, allow_none=True)
    from_department_id = fields.Int(validate=validate.Range(min=1), load_default=None, allow_none=True)
    # Required for employee_to_employee
    to_user_id = fields.Int(validate=validate.Range(min=1), load_default=None, allow_none=True)
    new_location = fields.Str(validate=validate.Length(max=255), allow_none=True)
    to_warehouse_id = fields.Int(validate=validate.Range(min=1), load_default=None, allow_none=True)
    to_bin_id = fields.Int(validate=validate.Range(min=1), load_default=None, allow_none=True)
    from_warehouse_id = fields.Int(validate=validate.Range(min=1), allow_none=True)
    comment = fields.Str(validate=validate.Length(max=1000), allow_none=True)

    @validates_schema
    def validate_type_fields(self, data, **kwargs):
        transfer_type = data.get("transfer_type")
        errors = {}
        if transfer_type == "employee_to_employee" and not data.get("to_user_id"):
            errors["to_user_id"] = ["Required for employee-to-employee transfers"]
        if transfer_type == "department_to_department" and not data.get("new_department_id"):
            errors["new_department_id"] = ["Required for department-to-department transfers"]
        if transfer_type == "warehouse_to_warehouse" and not data.get("to_warehouse_id"):
            errors["to_warehouse_id"] = ["Required for warehouse-to-warehouse transfers"]
        if errors:
            raise ValidationError(errors)


class TransferReviewSchema(Schema):
    comments = fields.Str(validate=validate.Length(max=1000))


class InventoryItemSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    sku = fields.Str(
        validate=[
            validate.Length(min=1, max=100),
            validate.Regexp(
                r"^[a-zA-Z0-9\-_./ ]+$",
                error="SKU must contain only letters, numbers, hyphens, underscores, dots, slashes, and spaces",
            ),
        ]
    )
    description = fields.Str(validate=validate.Length(max=1000))
    quantity = fields.Int(validate=validate.Range(min=0))
    reorder_level = fields.Int(validate=validate.Range(min=0))
    unit_price = fields.Float(required=True, validate=validate.Range(min=0))
    unit = fields.Str(validate=validate.Length(max=50))
    category_id = fields.Int(validate=validate.Range(min=1), allow_none=True)
    item_type = fields.Str(validate=validate.OneOf(["consumable", "asset", "raw", "finished", "service", "other"]), load_default="consumable")
    status = fields.Str(validate=validate.Length(max=50), load_default="active")
    preferred_supplier_id = fields.Int(validate=validate.Range(min=1), allow_none=True)
    supplier_item_reference = fields.Str(validate=validate.Length(max=255), allow_none=True)
    purchase_cost = fields.Float(validate=validate.Range(min=0), allow_none=True)
    last_purchase_cost = fields.Float(validate=validate.Range(min=0), allow_none=True)
    tax_category = fields.Str(validate=validate.Length(max=100), allow_none=True)
    lead_time_days = fields.Int(validate=validate.Range(min=0), allow_none=True)
    min_stock_level = fields.Int(validate=validate.Range(min=0), allow_none=True)
    max_stock_level = fields.Int(validate=validate.Range(min=0), allow_none=True)
    safety_stock = fields.Int(validate=validate.Range(min=0), allow_none=True)
    opening_stock = fields.Int(validate=validate.Range(min=0), allow_none=True)
    warehouse_id = fields.Int(validate=validate.Range(min=1), allow_none=True)
    warehouse_name = fields.Str(validate=validate.Length(max=255), allow_none=True, load_default=None)
    batch_tracking = fields.Boolean(load_default=False)
    serial_tracking = fields.Boolean(load_default=False)
    expiry_tracking = fields.Boolean(load_default=False)

    # Nullable integer fields that CSV parsing can deliver as empty strings or
    # non-numeric text (e.g. a warehouse *name* instead of its numeric ID).
    _NULLABLE_INT_FIELDS = (
        "category_id", "preferred_supplier_id", "lead_time_days",
        "min_stock_level", "max_stock_level", "safety_stock",
        "opening_stock", "warehouse_id", "quantity", "reorder_level",
    )
    _NULLABLE_FLOAT_FIELDS = (
        "unit_price", "purchase_cost", "last_purchase_cost",
    )

    @pre_load
    def coerce_numeric_strings(self, data, **kwargs):
        """Convert empty strings → None and numeric strings → proper types.

        This makes the schema resilient to CSV-parsed data where every cell
        arrives as a string and optional cells arrive as an empty string "".
        """
        result = dict(data)
        for field in self._NULLABLE_INT_FIELDS:
            val = result.get(field)
            if val == "" or val is None:
                result[field] = None
            elif isinstance(val, str):
                try:
                    result[field] = int(val)
                except (ValueError, TypeError):
                    # Leave as-is so Marshmallow can produce a proper error msg
                    pass
        for field in self._NULLABLE_FLOAT_FIELDS:
            val = result.get(field)
            if val == "" or val is None:
                result[field] = None
            elif isinstance(val, str):
                try:
                    result[field] = float(val)
                except (ValueError, TypeError):
                    pass
        return result


class StockMovementSchema(Schema):
    type = fields.Str(required=True, validate=validate.OneOf(["IN", "OUT"]))
    quantity = fields.Int(required=True, validate=validate.Range(min=1))
    warehouse_id = fields.Int(validate=validate.Range(min=1))
    # For OUT movements that are warehouse transfers, specify the receiving warehouse
    destination_warehouse_id = fields.Int(validate=validate.Range(min=1), allow_none=True)
    reference = fields.Str(validate=validate.Length(max=255))
    notes = fields.Str(validate=validate.Length(max=1000))


class InventoryBatchSchema(Schema):
    """Schema for inventory batch operations"""
    batch_number = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    item_id = fields.Int(required=True, validate=validate.Range(min=1))
    quantity = fields.Int(required=True, validate=validate.Range(min=0))
    warehouse_id = fields.Int(validate=validate.Range(min=1), allow_none=True)
    received_date = fields.DateTime(format='%Y-%m-%dT%H:%M:%S', required=True)
    manufacture_date = fields.DateTime(format='%Y-%m-%dT%H:%M:%S', allow_none=True)
    expiry_date = fields.DateTime(format='%Y-%m-%dT%H:%M:%S', allow_none=True)
    supplier_id = fields.Int(validate=validate.Range(min=1), allow_none=True)
    status = fields.Str(validate=validate.OneOf(['available', 'reserved', 'used', 'expired', 'discarded']), load_default='available')

    @validates_schema
    def validate_dates(self, data, **kwargs):
        """Ensure manufacture_date and expiry_date are after received_date"""
        if data.get('manufacture_date') and data.get('received_date'):
            if data['manufacture_date'] < data['received_date']:
                raise ValidationError('Manufacture date must be on or after received date', 'manufacture_date')
        if data.get('expiry_date') and data.get('received_date'):
            if data['expiry_date'] < data['received_date']:
                raise ValidationError('Expiry date must be on or after received date', 'expiry_date')


class TransferSchema(Schema):
    asset_id = fields.Int(required=True, validate=validate.Range(min=1))
    new_department_id = fields.Int(
        required=True, validate=validate.Range(min=1)
    )
    new_location = fields.Str(validate=validate.Length(max=255))


# Validation functions
def validate_input(schema_class, data):
    """Validate input data against schema"""
    schema = schema_class()
    try:
        validated_data = schema.load(data)
        return validated_data, None
    except ValidationError as err:
        return None, err.messages


def sanitize_string(value):
    """Sanitize string input"""
    if not isinstance(value, str):
        return value
    # Remove potentially dangerous characters
    return re.sub(r"[<>]", "", value.strip())
