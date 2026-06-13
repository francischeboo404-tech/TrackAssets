import re

from marshmallow import EXCLUDE, Schema, ValidationError, fields, pre_load, validate


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
                "requested",
                "approved",
                "rejected",
                "in_use",
                "maintenance",
                "disposed",
            ]
        ),
    )
    comments = fields.Str(validate=validate.Length(max=1000), allow_none=True)


class TransferRequestSchema(Schema):
    item_type = fields.Str(validate=validate.OneOf(["asset", "inventory"]), missing="asset")
    asset_id = fields.Int(validate=validate.Range(min=1), allow_none=True)
    inventory_item_id = fields.Int(validate=validate.Range(min=1), allow_none=True)
    quantity = fields.Int(validate=validate.Range(min=1), missing=1)
    new_department_id = fields.Int(
        required=True, validate=validate.Range(min=1)
    )
    new_location = fields.Str(validate=validate.Length(max=255), allow_none=True)
    to_warehouse_id = fields.Int(validate=validate.Range(min=1), allow_none=True)
    to_bin_id = fields.Int(validate=validate.Range(min=1), allow_none=True)
    from_warehouse_id = fields.Int(validate=validate.Range(min=1), allow_none=True)
    comment = fields.Str(validate=validate.Length(max=1000), allow_none=True)


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


class StockMovementSchema(Schema):
    type = fields.Str(required=True, validate=validate.OneOf(["IN", "OUT"]))
    quantity = fields.Int(required=True, validate=validate.Range(min=1))
    warehouse_id = fields.Int(validate=validate.Range(min=1))
    reference = fields.Str(validate=validate.Length(max=255))
    notes = fields.Str(validate=validate.Length(max=1000))


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
