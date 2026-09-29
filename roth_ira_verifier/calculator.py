"""
Calculation engine for fund return verification.

Computes expected track-level returns and simulates member balance
day-by-day using actual market data.
"""

import datetime

import numpy as np
import pandas as pd

from .parser import ReportData
from .market_data import nearest_trading_day


def calculate_track_return(
    report: ReportData, data: pd.DataFrame
) -> dict:
    """
    Calculate what the track SHOULD have returned based on actual
    index performance in ILS.

    Returns a dict with period returns, monthly breakdown, and comparison
    to the reported track return.
    """
    baseline = nearest_trading_day(data.index, report.period_start, "on_or_before")
    if baseline >= report.period_start:
        baseline = max(d for d in data.index if d < report.period_start)
    end_day = nearest_trading_day(data.index, report.period_end, "on_or_before")

    idx_s = float(data.loc[baseline, "index_price"])
    idx_e = float(data.loc[end_day, "index_price"])
    tr_s = float(data.loc[baseline, "total_return_price"])
    tr_e = float(data.loc[end_day, "total_return_price"])
    fx_s = float(data.loc[baseline, "usdils"])
    fx_e = float(data.loc[end_day, "usdils"])

    idx_ret = idx_e / idx_s - 1
    tr_ret = tr_e / tr_s - 1
    fx_chg = fx_e / fx_s - 1

    idx_ils = (1 + idx_ret) * (1 + fx_chg) - 1
    tr_ils = (1 + tr_ret) * (1 + fx_chg) - 1

    reported = report.reported_track_return_pct / 100
    gap_price = reported - idx_ils
    gap_total = reported - tr_ils

    # Monthly breakdown
    start_year = report.period_start.year
    start_month = report.period_start.month
    end_month = report.period_end.month
    if report.period_end.year > start_year:
        end_month += 12 * (report.period_end.year - start_year)

    monthly = []
    for offset in range(end_month - start_month + 1):
        m = start_month + offset
        y = start_year + (m - 1) // 12
        m = ((m - 1) % 12) + 1

        m_start = datetime.date(y, m, 1)
        if m == 12:
            m_end_date = datetime.date(y, 12, 31)
        else:
            m_end_date = datetime.date(y, m + 1, 1) - datetime.timedelta(days=1)

        prev = nearest_trading_day(data.index, m_start, "on_or_before")
        if prev >= m_start:
            prev = max(d for d in data.index if d < m_start)
        last = nearest_trading_day(data.index, m_end_date, "on_or_before")

        g_s = float(data.loc[prev, "index_price"])
        g_e = float(data.loc[last, "index_price"])
        s_s = float(data.loc[prev, "total_return_price"])
        s_e = float(data.loc[last, "total_return_price"])
        f_s = float(data.loc[prev, "usdils"])
        f_e = float(data.loc[last, "usdils"])

        g_ret = g_e / g_s - 1
        s_ret = s_e / s_s - 1
        f_chg = f_e / f_s - 1
        g_ils = (1 + g_ret) * (1 + f_chg) - 1
        s_ils = (1 + s_ret) * (1 + f_chg) - 1

        month_name = datetime.date(y, m, 1).strftime("%B %Y")
        monthly.append({
            "month": month_name,
            "index_usd": g_ret,
            "total_return_usd": s_ret,
            "fx": f_chg,
            "index_ils": g_ils,
            "total_return_ils": s_ils,
        })

    return dict(
        baseline=baseline,
        end=end_day,
        index_start=idx_s,
        index_end=idx_e,
        total_return_start=tr_s,
        total_return_end=tr_e,
        fx_start=fx_s,
        fx_end=fx_e,
        index_ret=idx_ret,
        total_return_ret=tr_ret,
        fx_chg=fx_chg,
        index_ils=idx_ils,
        total_return_ils=tr_ils,
        reported=reported,
        gap_price=gap_price,
        gap_total=gap_total,
        monthly=monthly,
    )


def simulate_member_balance(
    report: ReportData, data: pd.DataFrame
) -> dict:
    """
    Day-by-day simulation of the member balance using real market returns.

    Applies deposits on actual dates, deducts prorated management fees,
    and compares the result to the reported ending balance.
    """
    period_dates = sorted(
        d for d in data.index
        if report.period_start <= d <= report.period_end
    )
    n_days = len(period_dates)
    if n_days == 0:
        raise ValueError("No trading days found in the report period")

    deposit_map = {}
    for dep in report.deposits:
        td = nearest_trading_day(data.index, dep.date, "on_or_after")
        if td not in period_dates:
            td = min(period_dates, key=lambda x, t=dep.date: abs((x - t).days))
        deposit_map[td] = dep.total

    daily_sav_rate = (report.mgmt_fee_savings_pct / 100) / 365
    dep_fee_rate = report.mgmt_fee_deposits_pct / 100

    def simulate_with_returns(return_col: str):
        bal = float(report.opening_balance)
        totals = dict(mkt=0.0, sav_fee=0.0, dep_fee=0.0, dep_gross=0.0, dep_net=0.0)
        rows = []

        for date in period_dates:
            dr = float(data.loc[date, return_col])
            if np.isnan(dr):
                dr = 0.0

            mkt = bal * dr
            sf = bal * daily_sav_rate
            bal += mkt - sf
            totals["mkt"] += mkt
            totals["sav_fee"] += sf

            dg = deposit_map.get(date, 0)
            dfee = dg * dep_fee_rate
            dn = dg - dfee
            bal += dn
            totals["dep_gross"] += dg
            totals["dep_net"] += dn
            totals["dep_fee"] += dfee

            rows.append(dict(
                date=date,
                daily_pct=dr * 100,
                mkt=mkt,
                sav_fee=sf,
                dep_gross=dg,
                dep_fee=dfee,
                dep_net=dn,
                balance=bal,
            ))

        return bal, totals, pd.DataFrame(rows)

    bal_price, t_price, log_price = simulate_with_returns("index_ils_ret")
    bal_total, t_total, log_total = simulate_with_returns("total_return_ils_ret")

    # Cross-check: simulate using reported track return
    r_daily = (1 + report.reported_track_return_pct / 100) ** (1 / n_days) - 1
    r_bal = float(report.opening_balance)
    for date in period_dates:
        r_bal += r_bal * r_daily - r_bal * daily_sav_rate
        dg = deposit_map.get(date, 0)
        r_bal += dg * (1 - dep_fee_rate)

    return dict(
        log_price=log_price,
        log_total=log_total,
        bal_price=bal_price,
        bal_total=bal_total,
        totals_price=t_price,
        totals_total=t_total,
        reported_check=r_bal,
        actual=report.ending_balance,
        gap_price=bal_price - report.ending_balance,
        gap_total=bal_total - report.ending_balance,
        total_fees_price=t_price["sav_fee"] + t_price["dep_fee"],
        total_fees_total=t_total["sav_fee"] + t_total["dep_fee"],
    )
