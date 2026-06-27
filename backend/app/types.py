from decimal import Decimal, InvalidOperation
from sqlalchemy.types import TypeDecorator, Numeric, String


class SafeNumeric(TypeDecorator):
    """Dialect-aware numeric type.

    - On PostgreSQL (and other DBs that support exact numerics) this uses
      the native `Numeric(precision, scale)` type and returns Python
      Decimal objects.
    - On SQLite it stores values as text (decimal strings) to avoid
      lossy float conversions and the SAWarning about Decimal support.
    """

    impl = Numeric
    cache_ok = True

    def __init__(self, precision, scale, **kwargs):
        super().__init__(**kwargs)
        self.precision = precision
        self.scale = scale

    def load_dialect_impl(self, dialect):
        if dialect.name == "sqlite":
            # store as text on sqlite to preserve exact decimal representation
            return dialect.type_descriptor(String(50))
        return dialect.type_descriptor(Numeric(self.precision, self.scale))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        try:
            dec = Decimal(str(value))
        except (InvalidOperation, TypeError):
            dec = Decimal(0)

        if dialect.name == "sqlite":
            # Return a fixed-scale decimal string (e.g. '123.45')
            quant = Decimal(1).scaleb(-self.scale)
            dec_q = dec.quantize(quant)
            return format(dec_q, "f")

        # For other dialects keep Decimal so DB driver can handle it
        return dec

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        # Convert whatever we get back into Decimal for application code
        return Decimal(str(value))
