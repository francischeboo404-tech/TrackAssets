"""
Professional document export helpers for CSV and shared metadata blocks.

CSV layout:
  Row 1–4: Report title, organization, generated timestamp, blank
  Row 5: Column headings
  Row 6+: Data rows
"""

from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Iterable, List, Optional, Sequence


CSV_BOM = "\ufeff"
TRACKIT_BRAND = "TrackIT — Nova Lite Limited"


def _format_generated_at() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


def build_csv_document(
    report_title: str,
    organization_name: str,
    column_headers: Sequence[str],
    data_rows: Iterable[Sequence],
    *,
    subtitle: Optional[str] = None,
    extra_meta: Optional[List[str]] = None,
) -> str:
    """Build a complete CSV string with metadata block and header row on top of data."""
    output = io.StringIO()
    output.write(CSV_BOM)
    writer = csv.writer(output, lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)

    writer.writerow([TRACKIT_BRAND])
    writer.writerow([report_title])
    writer.writerow([f"Organization: {organization_name}"])
    if subtitle:
        writer.writerow([subtitle])
    writer.writerow([f"Generated: {_format_generated_at()}"])
    if extra_meta:
        for line in extra_meta:
            writer.writerow([line])
    writer.writerow([])

    writer.writerow(list(column_headers))
    for row in data_rows:
        writer.writerow(list(row))

    content = output.getvalue()
    output.close()
    return content


def build_csv_multi_section(
    report_title: str,
    organization_name: str,
    sections: List[dict],
    *,
    subtitle: Optional[str] = None,
) -> str:
    """
    sections: [{ "title": str, "headers": [...], "rows": [[...], ...] }, ...]
    """
    output = io.StringIO()
    output.write(CSV_BOM)
    writer = csv.writer(output, lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)

    writer.writerow([TRACKIT_BRAND])
    writer.writerow([report_title])
    writer.writerow([f"Organization: {organization_name}"])
    if subtitle:
        writer.writerow([subtitle])
    writer.writerow([f"Generated: {_format_generated_at()}"])
    writer.writerow([])

    for index, section in enumerate(sections):
        if index > 0:
            writer.writerow([])
        writer.writerow([f"=== {section['title']} ==="])
        writer.writerow(list(section["headers"]))
        for row in section.get("rows", []):
            writer.writerow(list(row))

    content = output.getvalue()
    output.close()
    return content


def format_currency(amount, currency: str = "KES") -> str:
    try:
        value = float(amount or 0)
    except (TypeError, ValueError):
        value = 0.0
    return f"{currency} {value:,.2f}"


def format_status_label(status: Optional[str]) -> str:
    if not status:
        return ""
    return str(status).replace("_", " ").title()
