from decimal import Decimal, InvalidOperation

THREE_PLACES = Decimal("0.001")


def parse_quantity_value(value: object) -> Decimal | None:
  if value is None:
    return None

  if isinstance(value, float):
    import math
    if math.isnan(value):
      return None

  try:
    qty = Decimal(str(value).replace(",", ".").strip())
  except (InvalidOperation, ValueError, TypeError):
    return None

  if qty < 0:
    return None

  return qty.quantize(THREE_PLACES)


def format_quantity(value: Decimal | float | int) -> str:
  qty = Decimal(str(value)).quantize(THREE_PLACES)
  text = f"{qty:.3f}".rstrip("0").rstrip(".")
  return text or "0"
