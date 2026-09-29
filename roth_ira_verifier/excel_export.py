"""
Excel export for fund return verification analysis.

Generates a multi-sheet Excel workbook with detailed data.
"""

from pathlib import Path
from typing import Union

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter

from .parser import ReportData


def _fmt_ils(val) -> str:
    return f"\u20aa{val:,.0f}"


def _fmt_pct(val, decimals=2) -> str:
    return f"{val * 100:.{decimals}f}%"


def generate_excel(
    report: ReportData,
    track: dict,
    member: dict,
    data: pd.DataFrame,
    output_path: Union[str, Path],
):
    """Generate a multi-sheet Excel workbook with the analysis data."""
    wb = Workbook()
    hdr_fill = PatternFill("solid", fgColor="1a365d")
    hdr_font = Font(bold=True, size=11, color="FFFFFF")
    num_fmt = "#,##0"
    pct_fmt = "0.00%"

    def write_header(ws, headers, row=1):
        for c, h in enumerate(headers, 1):
            cell = ws.cell(row=row, column=c, value=h)
            cell.font = hdr_font
            cell.fill = hdr_fill
            cell.alignment = Alignment(horizontal="center")

    def auto_width(ws):
        for col_cells in ws.columns:
            length = max(len(str(c.value or "")) for c in col_cells) + 2
            ws.column_dimensions[get_column_letter(col_cells[0].column)].width = min(
                length, 30
            )

    # -- Summary --
    ws = wb.active
    ws.title = "Summary"
    rows = [
        ("Period", f"{report.period_start} to {report.period_end}"),
        ("Member", f"{report.member_name} (ID {report.id_number})"),
        ("Fund / Track", f"{report.fund_name} / {report.track_name}"),
        ("", ""),
        ("=== TRACK-LEVEL ANALYSIS ===", ""),
        ("Index price return (USD)", _fmt_pct(track["index_ret"])),
        ("Total return (USD, incl. dividends)", _fmt_pct(track["total_return_ret"])),
        ("USD/ILS change", _fmt_pct(track["fx_chg"])),
        ("Expected ILS return (price)", _fmt_pct(track["index_ils"])),
        ("Expected ILS return (total)", _fmt_pct(track["total_return_ils"])),
        ("Reported track return", _fmt_pct(track["reported"])),
        ("Diff vs price return", _fmt_pct(track["gap_price"])),
        ("Diff vs total return", _fmt_pct(track["gap_total"])),
        ("", ""),
        ("=== MEMBER-LEVEL ANALYSIS ===", ""),
        ("Opening balance", _fmt_ils(report.opening_balance)),
        ("Total deposits", _fmt_ils(report.total_deposits)),
        ("Expected balance (price)", _fmt_ils(member["bal_price"])),
        ("Expected balance (total)", _fmt_ils(member["bal_total"])),
        ("Actual balance", _fmt_ils(report.ending_balance)),
        ("Diff (price)", _fmt_ils(member["gap_price"])),
        ("Diff (total)", _fmt_ils(member["gap_total"])),
        ("Cross-check (reported % applied)", _fmt_ils(member["reported_check"])),
    ]
    for r, (label, value) in enumerate(rows, 1):
        cell = ws.cell(row=r, column=1, value=label)
        if label.startswith("==="):
            cell.font = Font(bold=True, size=12)
        ws.cell(row=r, column=2, value=value)
    auto_width(ws)

    # -- Monthly Returns --
    ws2 = wb.create_sheet("Monthly Returns")
    write_header(
        ws2,
        ["Month", "Index (USD)", "Total Return (USD)", "USD/ILS Chg", "ILS Return (total)"],
    )
    for r, m in enumerate(track["monthly"], 2):
        ws2.cell(row=r, column=1, value=m["month"])
        for c, key in enumerate(
            ["index_usd", "total_return_usd", "fx", "total_return_ils"], 2
        ):
            ws2.cell(row=r, column=c, value=m[key]).number_format = pct_fmt
    auto_width(ws2)

    # -- Deposits --
    ws3 = wb.create_sheet("Deposits")
    write_header(ws3, ["Date", "Salary Month", "Employee", "Employer", "Total"])
    for r, d in enumerate(report.deposits, 2):
        ws3.cell(row=r, column=1, value=d.date.isoformat())
        ws3.cell(row=r, column=2, value=d.salary_month)
        ws3.cell(row=r, column=3, value=d.employee).number_format = num_fmt
        ws3.cell(row=r, column=4, value=d.employer).number_format = num_fmt
        ws3.cell(row=r, column=5, value=d.total).number_format = num_fmt
    auto_width(ws3)

    # -- Daily Simulation --
    ws4 = wb.create_sheet("Daily Simulation")
    write_header(
        ws4,
        ["Date", "Daily %", "Mkt Gain", "Sav Fee", "Deposit", "Balance"],
    )
    for r, row in member["log_total"].iterrows():
        rn = r + 2
        ws4.cell(row=rn, column=1, value=row["date"].isoformat())
        ws4.cell(row=rn, column=2, value=row["daily_pct"]).number_format = "0.000"
        for c, col in enumerate(["mkt", "sav_fee", "dep_gross", "balance"], 3):
            ws4.cell(row=rn, column=c, value=row[col]).number_format = num_fmt
    auto_width(ws4)

    # -- Market Data --
    ws5 = wb.create_sheet("Market Data")
    period = data[
        (data.index >= report.period_start) & (data.index <= report.period_end)
    ]
    write_header(
        ws5,
        ["Date", "Index Price", "Total Return Price", "USD/ILS", "Index (ILS)", "Total Return (ILS)"],
    )
    for r, (date, row) in enumerate(period.iterrows(), 2):
        ws5.cell(row=r, column=1, value=date.isoformat())
        ws5.cell(row=r, column=2, value=row["index_price"]).number_format = "#,##0.00"
        ws5.cell(row=r, column=3, value=row["total_return_price"]).number_format = "#,##0.00"
        ws5.cell(row=r, column=4, value=row["usdils"]).number_format = "0.0000"
        ws5.cell(row=r, column=5, value=row["index_ils"]).number_format = "#,##0.00"
        ws5.cell(row=r, column=6, value=row["total_return_ils"]).number_format = "#,##0.00"
    auto_width(ws5)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    print(f"  Excel    -> {output_path}")
