import sys
from pathlib import Path

from .parser import parse_report
from .market_data import fetch_market_data
from .calculator import calculate_track_return, simulate_member_balance
from .report_generator import generate_html_report
from .excel_export import generate_excel

OUTPUT_DIR = Path("output")


def _fmt_ils(val):
    return f"\u20aa{val:,.0f}"


def _fmt_pct(val, decimals=2):
    return f"{val * 100:.{decimals}f}%"


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 verify.py <translated_report_file>")
        print('Example: python3 verify.py "reports/translated-q3-2025.md"')
        sys.exit(1)

    report_file = sys.argv[1]
    print("=" * 60)
    print("  Keren Hishtalmut Return Verification")
    print("=" * 60)
    print()

    print("[1/5] Parsing report ...")
    report = parse_report(report_file)
    print(f"  Fund:     {report.fund_name}")
    print(f"  Track:    {report.track_name}")
    print(f"  Period:   {report.period_start} to {report.period_end}")
    print(f"  Opening:  {_fmt_ils(report.opening_balance)}")
    print(f"  Deposits: {_fmt_ils(report.total_deposits)} ({len(report.deposits)} deposits)")
    print(f"  Reported: {report.reported_track_return_pct}% return, {_fmt_ils(report.reported_profit)} profit")
    print(f"  Ending:   {_fmt_ils(report.ending_balance)}")
    print(f"  Fees:     {report.mgmt_fee_savings_pct}% savings")
    print()

    print("[2/5] Fetching market data ...")
    data = fetch_market_data(report.track_name, report.period_start, report.period_end)
    print()

    print("[3/5] Calculating expected returns ...")
    track = calculate_track_return(report, data)
    print(f"  Index price return (USD):  {_fmt_pct(track['index_ret'])}")
    print(f"  Total return (USD):        {_fmt_pct(track['total_return_ret'])}")
    print(f"  USD/ILS change:            {_fmt_pct(track['fx_chg'])}")
    print(f"  Expected ILS (price):      {_fmt_pct(track['index_ils'])}")
    print(f"  Expected ILS (total):      {_fmt_pct(track['total_return_ils'])}")
    print(f"  Reported:                  {_fmt_pct(track['reported'])}")
    print(f"  Diff (vs total):           {_fmt_pct(track['gap_total'])}")
    print()

    print("[4/5] Simulating member balance ...")
    member = simulate_member_balance(report, data)
    print(f"  Expected balance (total):  {_fmt_ils(member['bal_total'])}")
    print(f"  Actual balance:            {_fmt_ils(report.ending_balance)}")
    print(f"  Difference:                {_fmt_ils(member['gap_total'])}")
    print(f"  Cross-check (reported %):  {_fmt_ils(member['reported_check'])}")
    print()

    print("[5/5] Generating reports ...")
    OUTPUT_DIR.mkdir(exist_ok=True)
    generate_html_report(report, track, member, OUTPUT_DIR / "report.html")
    generate_excel(report, track, member, data, OUTPUT_DIR / "analysis.xlsx")
    print()

    print("\u2501" * 60)
    gap = abs(track["gap_total"])
    if gap < 0.005:
        result = "CONSISTENT"
    elif gap < 0.01:
        result = "MINOR DIFFERENCE"
    else:
        result = "DISCREPANCY"

    print(f"  Result: {result}")
    print(f"  Expected (ILS total): {_fmt_pct(track['total_return_ils'])}")
    print(f"  Reported:             {_fmt_pct(track['reported'])}")
    print(f"  Difference:           {_fmt_pct(track['gap_total'])}")
    if result == "CONSISTENT":
        print()
        print("  The reported return is within normal tracking range.")
    elif result == "DISCREPANCY":
        print()
        print("  SIGNIFICANT DISCREPANCY - review the HTML report for details.")
    print("\u2501" * 60)
