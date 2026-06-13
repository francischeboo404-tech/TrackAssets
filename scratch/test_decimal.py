from decimal import Decimal
from datetime import date, datetime

purchase_value = Decimal('100000.00')
useful_life = 5
purchase_date = date(2023, 1, 1)
years_used = (date(2024, 1, 1) - purchase_date).days / 365.25

try:
    annual_depreciation = purchase_value / useful_life
    depreciated_value = purchase_value - (annual_depreciation * years_used)
    print(f"Depreciated value: {depreciated_value}")
except TypeError as e:
    print(f"Caught expected TypeError: {e}")

# Correct way
from decimal import Decimal, getcontext
years_used_dec = Decimal(str(years_used))
depreciated_value_correct = purchase_value - (annual_depreciation * years_used_dec)
print(f"Corrected Depreciated value: {depreciated_value_correct}")
