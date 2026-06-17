from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

import pandas as pd

from app.logging_config import get_logger
from app.utils.quantity import parse_quantity_value

logger = get_logger(__name__)

REQUIRED_COLUMNS = ["Филиал", "Поставщик", "Дата", "Наименование", "Кол-во"]

# Alternative header names seen in real pharmacy exports.
COLUMN_ALIASES: dict[str, list[str]] = {
  "Филиал": ["Филиал", "Филиалы"],
  "Поставщик": ["Поставщик", "Поставщики"],
  "Дата": ["Дата", "Дата отчета", "Дата отчёта"],
  "Наименование": ["Наименование", "Наименование товара", "Товар"],
  "Кол-во": ["Кол-во", "Кол.во", "Количество", "Кол - во"],
}

MAX_HEADER_SCAN_ROWS = 30


@dataclass
class ImportRow:
  branch: str
  supplier: str
  report_date: datetime
  medicine: str
  quantity: Decimal


@dataclass
class ImportResult:
  rows_processed: int
  rows_skipped: int
  status: str
  error_message: str | None = None


class ExcelImportError(Exception):
  pass


def normalize_column_name(name: object) -> str:
  if name is None or (isinstance(name, float) and pd.isna(name)):
    return ""
  text = str(name).replace("\xa0", " ").replace("\u200b", "").strip()
  return " ".join(text.split())


def normalize_text(value: str | None) -> str:
  if value is None or (isinstance(value, float) and pd.isna(value)):
    return ""
  return str(value).strip()


def parse_date(value: object) -> datetime | None:
  if value is None or (isinstance(value, float) and pd.isna(value)):
    return None

  if isinstance(value, datetime):
    dt = value.to_pydatetime() if hasattr(value, "to_pydatetime") else value
  else:
    try:
      parsed = pd.to_datetime(value, dayfirst=True)
      if pd.isna(parsed):
        return None
      dt = parsed.to_pydatetime()
    except (ValueError, TypeError):
      return None

  if dt.tzinfo is None:
    return dt.replace(tzinfo=timezone.utc)
  return dt


def parse_quantity(value: object) -> Decimal | None:
  return parse_quantity_value(value)


def validate_file_extension(file_name: str) -> None:
  lower = file_name.lower()
  if not (lower.endswith(".xlsx") or lower.endswith(".xls")):
    raise ExcelImportError("Invalid file format. Only Excel files (.xlsx, .xls) are accepted.")


def _normalized_alias_set() -> dict[str, set[str]]:
  return {
    canonical: {normalize_column_name(alias) for alias in aliases}
    for canonical, aliases in COLUMN_ALIASES.items()
  }


def _find_header_row(preview: pd.DataFrame, alias_sets: dict[str, set[str]]) -> int | None:
  for idx in range(len(preview)):
    row_values = {
      normalize_column_name(value)
      for value in preview.iloc[idx].values
      if normalize_column_name(value)
    }
    if all(row_values.intersection(aliases) for aliases in alias_sets.values()):
      return idx
  return None


def _resolve_column_map(columns: list[str]) -> dict[str, str]:
  normalized_columns = {normalize_column_name(col): col for col in columns}
  column_map: dict[str, str] = {}
  missing: list[str] = []

  for canonical, aliases in COLUMN_ALIASES.items():
    actual_name = None
    for alias in aliases:
      normalized_alias = normalize_column_name(alias)
      if normalized_alias in normalized_columns:
        actual_name = normalized_columns[normalized_alias]
        break
    if actual_name is None:
      missing.append(canonical)
    else:
      column_map[canonical] = actual_name

  if missing:
    found = [str(col) for col in columns if normalize_column_name(col)]
    raise ExcelImportError(
      f"Missing required columns: {', '.join(missing)}. "
      f"Found columns: {', '.join(found)}"
    )

  return column_map


class ExcelImportService:
  def validate_and_read(self, file_path: str, file_name: str) -> list[ImportRow]:
    validate_file_extension(file_name)
    alias_sets = _normalized_alias_set()

    try:
      preview = pd.read_excel(
        file_path,
        header=None,
        nrows=MAX_HEADER_SCAN_ROWS,
        engine="openpyxl",
      )
    except Exception as exc:
      logger.error("excel_read_header_failed", file_name=file_name, error=str(exc))
      raise ExcelImportError(f"Failed to read Excel file: {exc}") from exc

    header_row = _find_header_row(preview, alias_sets)
    if header_row is None:
      first_row = [
        normalize_column_name(value)
        for value in preview.iloc[0].values
        if normalize_column_name(value)
      ]
      raise ExcelImportError(
        f"Could not find header row with required columns. "
        f"First row: {', '.join(first_row) or 'empty'}"
      )

    try:
      df = pd.read_excel(file_path, header=header_row, engine="openpyxl")
    except Exception as exc:
      logger.error("excel_read_failed", file_name=file_name, error=str(exc))
      raise ExcelImportError(f"Failed to read Excel file: {exc}") from exc

    column_map = _resolve_column_map(list(df.columns))

    rows: list[ImportRow] = []
    seen: set[tuple[str, str, str, str]] = set()
    skipped = 0

    for _, row in df.iterrows():
      branch = normalize_text(row[column_map["Филиал"]])
      supplier = normalize_text(row[column_map["Поставщик"]])
      medicine = normalize_text(row[column_map["Наименование"]])
      report_date = parse_date(row[column_map["Дата"]])
      quantity = parse_quantity(row[column_map["Кол-во"]])

      if not branch or not supplier or not medicine or report_date is None or quantity is None:
        skipped += 1
        continue

      dedup_key = (branch, supplier, medicine, report_date.isoformat())
      if dedup_key in seen:
        skipped += 1
        continue
      seen.add(dedup_key)

      rows.append(
        ImportRow(
          branch=branch,
          supplier=supplier,
          report_date=report_date,
          medicine=medicine,
          quantity=quantity,
        )
      )

    logger.info(
      "excel_parsed",
      file_name=file_name,
      header_row=header_row,
      rows_valid=len(rows),
      rows_skipped=skipped,
    )
    return rows
