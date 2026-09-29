"""
HTML report generator for Keren Hishtalmut return verification.

Produces a clear, professional HTML report comparing expected vs reported
fund returns, suitable for correspondence with the fund company.
"""

import datetime
from pathlib import Path
from typing import Union

from .parser import ReportData


def _fmt_ils(val) -> str:
    return f"\u20aa{val:,.0f}"


def _fmt_pct(val, decimals=2) -> str:
    return f"{val * 100:.{decimals}f}%"


def generate_html_report(
    report: ReportData,
    track: dict,
    member: dict,
    output_path: Union[str, Path],
) -> str:
    """Generate a full HTML verification report and write it to disk."""

    monthly_rows = ""
    for m in track["monthly"]:
        monthly_rows += (
            f'  <tr><td>{m["month"]}</td>'
            f'<td class="right mono">{m["index_usd"]*100:+.2f}%</td>'
            f'<td class="right mono">{m["total_return_usd"]*100:+.2f}%</td>'
            f'<td class="right mono">{m["fx"]*100:+.2f}%</td>'
            f'<td class="right mono">{m["total_return_ils"]*100:+.2f}%</td></tr>\n'
        )

    deposit_rows = ""
    for d in report.deposits:
        deposit_rows += (
            f'  <tr><td>{d.date.isoformat()}</td>'
            f'<td>{d.salary_month}</td>'
            f'<td class="right mono">{_fmt_ils(d.employee)}</td>'
            f'<td class="right mono">{_fmt_ils(d.employer)}</td>'
            f'<td class="right mono">{_fmt_ils(d.total)}</td></tr>\n'
        )

    t = member["totals_total"]

    gap_total_abs = abs(track["gap_total"])
    if gap_total_abs < 0.005:
        verdict = "CONSISTENT"
        verdict_class = "match"
        verdict_detail = "within normal tracking range"
    elif gap_total_abs < 0.01:
        verdict = "MINOR DIFFERENCE"
        verdict_class = "minor"
        verdict_detail = "small difference, likely tracking error"
    else:
        verdict = "DISCREPANCY"
        verdict_class = "discrepancy"
        verdict_detail = "significant gap requiring explanation"

    reported_pct = _fmt_pct(track["reported"])
    expected_total_pct = _fmt_pct(track["total_return_ils"])
    gap_total_pct = _fmt_pct(track["gap_total"])

    # Fee description
    fee_parts = []
    if report.mgmt_fee_savings_pct > 0:
        fee_parts.append(f"{report.mgmt_fee_savings_pct}% annual on savings")
    if report.mgmt_fee_deposits_pct > 0:
        fee_parts.append(f"{report.mgmt_fee_deposits_pct}% on deposits")
    fee_desc = ", ".join(fee_parts) if fee_parts else "none disclosed"

    html = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Fund Return Verification Report</title>
<style>
  :root {{
    --blue: #1a365d;
    --light-blue: #ebf8ff;
    --red: #c53030;
    --green: #276749;
    --orange: #c05621;
    --gray: #718096;
    --border: #e2e8f0;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Georgia', 'Times New Roman', serif;
    color: #1a202c;
    line-height: 1.6;
    max-width: 920px;
    margin: 0 auto;
    padding: 40px 30px;
    font-size: 14px;
  }}
  h1, h2, h3 {{ font-family: 'Helvetica Neue', Arial, sans-serif; }}
  h1 {{
    color: var(--blue);
    font-size: 24px;
    border-bottom: 3px solid var(--blue);
    padding-bottom: 8px;
    margin-bottom: 4px;
  }}
  .subtitle {{
    color: var(--gray);
    font-size: 13px;
    margin-bottom: 30px;
  }}
  h2 {{
    color: var(--blue);
    font-size: 18px;
    margin: 30px 0 12px;
    border-bottom: 1px solid var(--border);
    padding-bottom: 4px;
  }}
  h3 {{ font-size: 15px; margin: 16px 0 8px; }}
  p {{ margin: 6px 0; }}
  .exec-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 16px;
    margin: 20px 0;
  }}
  .exec-box {{
    border: 2px solid var(--border);
    border-radius: 8px;
    padding: 16px;
    text-align: center;
  }}
  .exec-box .label {{
    font-size: 11px; color: var(--gray);
    text-transform: uppercase; letter-spacing: 1px;
  }}
  .exec-box .value {{
    font-size: 28px; font-weight: bold; margin: 6px 0;
    font-family: 'Helvetica Neue', Arial, sans-serif;
  }}
  .exec-box.green .value {{ color: var(--green); }}
  .exec-box.blue .value {{ color: var(--blue); }}
  .exec-box.match {{ border-color: var(--green); background: #f0fff4; }}
  .exec-box.match .value {{ color: var(--green); }}
  .exec-box.minor {{ border-color: var(--orange); background: #fffaf0; }}
  .exec-box.minor .value {{ color: var(--orange); }}
  .exec-box.discrepancy {{ border-color: var(--red); background: #fff5f5; }}
  .exec-box.discrepancy .value {{ color: var(--red); }}
  .red {{ color: var(--red); font-weight: bold; }}
  .green {{ color: var(--green); font-weight: bold; }}
  .orange {{ color: var(--orange); font-weight: bold; }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
    font-size: 13px;
  }}
  th {{
    background: var(--blue);
    color: white;
    padding: 8px 10px;
    text-align: left;
    font-family: 'Helvetica Neue', Arial, sans-serif;
    font-weight: 600;
  }}
  td {{
    padding: 6px 10px;
    border-bottom: 1px solid var(--border);
  }}
  tr:nth-child(even) td {{ background: #f7fafc; }}
  .right {{ text-align: right; }}
  .mono {{ font-family: 'SF Mono', 'Consolas', monospace; font-size: 12px; }}
  .callout-green {{
    border-left: 4px solid var(--green);
    background: #f0fff4;
    padding: 12px 16px;
    margin: 16px 0;
    border-radius: 0 4px 4px 0;
  }}
  .callout-red {{
    border-left: 4px solid var(--red);
    background: #fff5f5;
    padding: 12px 16px;
    margin: 16px 0;
    border-radius: 0 4px 4px 0;
  }}
  .callout-orange {{
    border-left: 4px solid var(--orange);
    background: #fffaf0;
    padding: 12px 16px;
    margin: 16px 0;
    border-radius: 0 4px 4px 0;
  }}
  .callout-info {{
    border-left: 4px solid var(--blue);
    background: var(--light-blue);
    padding: 12px 16px;
    margin: 16px 0;
    border-radius: 0 4px 4px 0;
  }}
  .sn {{
    display: inline-block;
    background: var(--blue);
    color: white;
    width: 24px; height: 24px;
    text-align: center;
    border-radius: 50%;
    font-size: 13px;
    line-height: 24px;
    margin-right: 6px;
    font-family: 'Helvetica Neue', Arial, sans-serif;
  }}
  ol.points {{ margin: 10px 0 10px 20px; }}
  ol.points li {{ margin: 8px 0; }}
  .footer {{
    margin-top: 40px;
    padding-top: 16px;
    border-top: 1px solid var(--border);
    font-size: 11px;
    color: var(--gray);
  }}
  @media print {{
    body {{ padding: 20px; font-size: 12px; }}
    h2 {{ page-break-after: avoid; }}
    table {{ page-break-inside: avoid; }}
  }}
</style>
</head>
<body>

<h1>Fund Return Verification Report</h1>
<div class="subtitle">
  {report.fund_name} &mdash; {report.track_name}<br>
  Period: {report.period_start.isoformat()} to {report.period_end.isoformat()}<br>
  Member: {report.member_name} &nbsp;|&nbsp; ID: {report.id_number}<br>
  Employer: {report.employer}<br>
  Report generated: {datetime.date.today().isoformat()}
</div>

<h2><span class="sn">1</span> Executive Summary</h2>

<p>
  This report uses <strong>real market data from Yahoo Finance</strong>
  to independently verify the return reported by the
  <strong>{report.track_name}</strong> for the period
  {report.period_start.strftime("%B %Y")} &ndash; {report.period_end.strftime("%B %Y")}.
</p>

<div class="exec-grid">
  <div class="exec-box green">
    <div class="label">Expected Return</div>
    <div class="value">{expected_total_pct}</div>
    <div class="label">S&amp;P 500 total return<br>in ILS</div>
  </div>
  <div class="exec-box blue">
    <div class="label">Reported Return</div>
    <div class="value">{reported_pct}</div>
    <div class="label">Per quarterly report</div>
  </div>
  <div class="exec-box {verdict_class}">
    <div class="label">Verdict</div>
    <div class="value">{gap_total_pct}</div>
    <div class="label">{verdict_detail}</div>
  </div>
</div>

{"" if verdict == "DISCREPANCY" else f'''
<div class="callout-green">
  <strong>Finding:</strong> The reported track return of <strong>{reported_pct}</strong>
  is broadly consistent with the actual S&amp;P 500 performance in ILS.
  The index returned <strong>{_fmt_pct(track["total_return_ret"])}</strong> in USD,
  but the USD moved <strong>{_fmt_pct(track["fx_chg"])}</strong> against the ILS,
  resulting in an ILS-denominated return of approximately <strong>{expected_total_pct}</strong>.
  The difference of <strong>{gap_total_pct}</strong> is {verdict_detail}.
</div>
'''}

{"" if verdict != "DISCREPANCY" else f'''
<div class="callout-red">
  <strong>Discrepancy Found:</strong> The reported track return of <strong>{reported_pct}</strong>
  differs significantly from the expected S&amp;P 500 ILS return of <strong>{expected_total_pct}</strong>.
  The gap of <strong>{gap_total_pct}</strong> cannot be fully explained by normal tracking error,
  cash drag, or timing differences. A detailed explanation from the fund is warranted.
</div>
'''}

<h2><span class="sn">2</span> Market Data (Yahoo Finance)</h2>

<h3>Period Overview</h3>
<table>
  <tr><th>Metric</th><th>Start ({track["baseline"]})</th><th>End ({track["end"]})</th><th class="right">Change</th></tr>
  <tr>
    <td>S&amp;P 500 Index (price)</td>
    <td class="right mono">{track["index_start"]:,.2f}</td>
    <td class="right mono">{track["index_end"]:,.2f}</td>
    <td class="right mono green">{_fmt_pct(track["index_ret"])}</td>
  </tr>
  <tr>
    <td>S&amp;P 500 Total Return (SPY adj.)</td>
    <td class="right mono">{track["total_return_start"]:,.2f}</td>
    <td class="right mono">{track["total_return_end"]:,.2f}</td>
    <td class="right mono green">{_fmt_pct(track["total_return_ret"])}</td>
  </tr>
  <tr>
    <td>USD/ILS Exchange Rate</td>
    <td class="right mono">{track["fx_start"]:.4f}</td>
    <td class="right mono">{track["fx_end"]:.4f}</td>
    <td class="right mono {"red" if track["fx_chg"] < 0 else "green"}">{_fmt_pct(track["fx_chg"])}</td>
  </tr>
</table>

<h3>Monthly Returns Breakdown</h3>
<table>
  <tr>
    <th>Month</th>
    <th class="right">Index (USD)</th>
    <th class="right">Total Return (USD)</th>
    <th class="right">USD/ILS Change</th>
    <th class="right">ILS Return (total)</th>
  </tr>
{monthly_rows}  <tr style="font-weight:bold; border-top: 2px solid var(--blue);">
    <td>Cumulative</td>
    <td class="right mono">{_fmt_pct(track["index_ret"])}</td>
    <td class="right mono">{_fmt_pct(track["total_return_ret"])}</td>
    <td class="right mono">{_fmt_pct(track["fx_chg"])}</td>
    <td class="right mono">{expected_total_pct}</td>
  </tr>
</table>

<div class="callout-info">
  <strong>Why the ILS return differs from the USD return:</strong>
  The USD/ILS rate moved from {track["fx_start"]:.4f} to {track["fx_end"]:.4f} during the period
  ({_fmt_pct(track["fx_chg"])}). For an Israeli investor, currency movement
  {"reduced" if track["fx_chg"] < 0 else "increased"} the return significantly.
  The formula:<br><br>
  <span class="mono">ILS Return = (1 + {_fmt_pct(track["total_return_ret"])}) &times; (1 + {_fmt_pct(track["fx_chg"])}) &minus; 1 = {expected_total_pct}</span>
</div>

<h2><span class="sn">3</span> Track Return: Expected vs. Reported</h2>

<table>
  <tr><th>Component</th><th class="right">Value</th></tr>
  <tr><td>S&amp;P 500 price return (USD)</td><td class="right mono">{_fmt_pct(track["index_ret"])}</td></tr>
  <tr><td>S&amp;P 500 total return (USD, incl. dividends)</td><td class="right mono">{_fmt_pct(track["total_return_ret"])}</td></tr>
  <tr><td>USD/ILS exchange rate change</td><td class="right mono">{_fmt_pct(track["fx_chg"])}</td></tr>
  <tr><td><strong>Expected ILS return (price only)</strong></td><td class="right mono"><strong>{_fmt_pct(track["index_ils"])}</strong></td></tr>
  <tr><td><strong>Expected ILS return (total, incl. dividends)</strong></td><td class="right mono green"><strong>{expected_total_pct}</strong></td></tr>
  <tr style="border-top: 2px solid var(--blue);">
    <td><strong>Reported track return</strong></td>
    <td class="right mono"><strong>{reported_pct}</strong></td>
  </tr>
  <tr><td>Difference (reported &minus; price)</td><td class="right mono">{_fmt_pct(track["gap_price"])}</td></tr>
  <tr><td>Difference (reported &minus; total)</td><td class="right mono">{gap_total_pct}</td></tr>
</table>

<p>
  The reported return is stated as "after investment management expenses but before
  management fees." The expected ILS return range is between {_fmt_pct(track["index_ils"])}
  (price only, no dividends) and {expected_total_pct} (total return with dividends).
  The reported {reported_pct}
  {"falls within this range, which is expected." if track["gap_price"] >= 0 and track["gap_total"] <= 0 else
   "is close to this range. Minor deviations are normal due to tracking error, cash drag, and timing differences." if gap_total_abs < 0.01 else
   "falls outside the expected range, which warrants investigation."}
</p>

<h2><span class="sn">4</span> Member Balance Verification</h2>

<p>
  Day-by-day simulation of the member balance using real S&amp;P 500 ILS
  returns (total return basis), applying deposits on their actual dates:
</p>

<table>
  <tr><th>Item</th><th class="right">Amount (ILS)</th></tr>
  <tr><td>Opening balance</td><td class="right mono">{_fmt_ils(report.opening_balance)}</td></tr>
  <tr><td>Total deposits (gross)</td><td class="right mono">{_fmt_ils(report.total_deposits)}</td></tr>
  <tr><td>Market gains (total return basis)</td><td class="right mono green">{_fmt_ils(t["mkt"])}</td></tr>
  <tr><td>Less: management fee on savings ({report.mgmt_fee_savings_pct}% ann.)</td><td class="right mono">-{_fmt_ils(t["sav_fee"])}</td></tr>
{"  <tr><td>Less: management fee on deposits (" + str(report.mgmt_fee_deposits_pct) + "%)</td><td class='right mono'>-" + _fmt_ils(t["dep_fee"]) + "</td></tr>" if report.mgmt_fee_deposits_pct > 0 else ""}
  <tr style="border-top: 2px solid var(--blue);">
    <td><strong>Expected ending balance (total return)</strong></td>
    <td class="right mono green"><strong>{_fmt_ils(member["bal_total"])}</strong></td>
  </tr>
  <tr><td>Actual ending balance (per report)</td><td class="right mono"><strong>{_fmt_ils(report.ending_balance)}</strong></td></tr>
  <tr><td>Difference</td><td class="right mono">{_fmt_ils(member["gap_total"])}</td></tr>
  <tr><td><em>Cross-check: balance using reported {reported_pct}</em></td><td class="right mono"><em>{_fmt_ils(member["reported_check"])}</em></td></tr>
</table>

<h3>Deposit Schedule</h3>
<table>
  <tr><th>Date</th><th>Salary Month</th><th class="right">Employee</th><th class="right">Employer</th><th class="right">Total</th></tr>
{deposit_rows}  <tr style="font-weight:bold; border-top: 2px solid var(--blue);">
    <td colspan="4">Total</td>
    <td class="right mono">{_fmt_ils(report.total_deposits)}</td>
  </tr>
</table>

<h2><span class="sn">5</span> Conclusions</h2>

{"" if verdict == "DISCREPANCY" else f'''
<div class="callout-green">
  <strong>Conclusion:</strong> The reported track return of {reported_pct} is
  consistent with actual S&amp;P 500 performance in ILS for this period.
  The difference of {gap_total_pct} is within the normal range attributable
  to tracking error, cash management, FX source differences, and timing.
</div>
'''}

{"" if verdict != "DISCREPANCY" else f'''
<div class="callout-red">
  <strong>Conclusion:</strong> The reported track return of {reported_pct} shows
  a significant discrepancy of {gap_total_pct} versus the expected ILS return
  of {expected_total_pct}. This gap exceeds what can be explained by normal
  tracking error and operational costs.
</div>

<h3>Recommended Actions</h3>
<ol class="points">
  <li>Request a detailed mathematical breakdown from the fund: how the track return
      of {reported_pct} was calculated, including the index values and exchange rates used.</li>
  <li>Ask for confirmation that 100% of funds are invested in the S&amp;P 500 tracking
      strategy with no allocation to other assets or guaranteed return components.</li>
  <li>Request the daily NAV (Net Asset Value) history for the track during the period
      to compare against the index day by day.</li>
</ol>
'''}

<h2><span class="sn">6</span> Methodology</h2>
<table>
  <tr><th>Item</th><th>Detail</th></tr>
  <tr><td>Index price data</td><td>Yahoo Finance <code>^GSPC</code> (S&amp;P 500 price return index)</td></tr>
  <tr><td>Total return proxy</td><td>Yahoo Finance <code>SPY</code> (auto-adjusted for dividends/splits)</td></tr>
  <tr><td>USD/ILS data</td><td>Yahoo Finance <code>USDILS=X</code></td></tr>
  <tr><td>Baseline date</td><td>{track["baseline"]} (last trading day before period start)</td></tr>
  <tr><td>End date</td><td>{track["end"]}</td></tr>
  <tr><td>Deposit dates</td><td>From quarterly report, snapped to nearest trading day</td></tr>
  <tr><td>Management fees</td><td>{fee_desc}</td></tr>
  <tr><td>Balance simulation</td><td>Day-by-day compounding with prorated fees</td></tr>
</table>

<div class="footer">
  This report was generated programmatically using publicly available market data
  from Yahoo Finance. All calculations are reproducible. Data fetched on {datetime.date.today().isoformat()}.
</div>

</body>
</html>
"""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(f"  HTML report -> {output_path}")
    return html
