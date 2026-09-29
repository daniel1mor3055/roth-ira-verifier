"""
Parser for Migdal Keren Hishtalmut (Study Fund) translated quarterly reports.

Extracts structured financial data from English-translated report text
(Gemini/GPT translations of Hebrew PDF reports).
"""

import re
import datetime
from dataclasses import dataclass, field
from typing import List


@dataclass
class Deposit:
    date: datetime.date
    salary_month: str
    salary: int
    employee: int
    employer: int
    total: int


@dataclass
class ReportData:
    # Period
    period_start: datetime.date
    period_end: datetime.date

    # Member info
    member_name: str = ""
    id_number: str = ""
    account_number: str = ""
    employer: str = ""

    # Fund info
    fund_name: str = ""
    track_name: str = ""

    # Section B - Movements
    opening_balance: int = 0
    total_deposits: int = 0
    reported_profit: int = 0
    management_fees: int = 0
    ending_balance: int = 0

    # Section C - Fee rates
    mgmt_fee_savings_pct: float = 0.0  # annual %
    mgmt_fee_deposits_pct: float = 0.0  # % on deposits (0 for Keren Hishtalmut)

    # Section D - Track return
    reported_track_return_pct: float = 0.0

    # Section E - Deposits
    deposits: List[Deposit] = field(default_factory=list)


def _normalize_text(raw: str) -> str:
    """Collapse the messy multi-line markdown into cleaner text."""
    lines = raw.splitlines()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if stripped:
            cleaned.append(stripped)
    return "\n".join(cleaned)


def _parse_number(s: str) -> int:
    """Parse a number string like '61,844' or '-190' into an int."""
    s = s.strip().replace(",", "").replace("₪", "").replace("NIS", "")
    s = re.sub(r"<[^>]+>", "", s)  # strip HTML tags like <br>
    s = re.sub(r"\*+", "", s)  # strip markdown bold markers
    s = s.strip()
    if not s or s == "-":
        return 0
    return int(float(s))


def _parse_pct(s: str) -> float:
    """Parse a percentage string like '3.10%' or '0.32%' into a float."""
    s = s.strip().replace("%", "").replace("*", "")
    s = re.sub(r"<[^>]+>", "", s).strip()
    return float(s)


def _parse_date_dmy(s: str) -> datetime.date:
    """Parse DD/MM/YYYY date, handling 2-digit years."""
    s = s.strip()
    parts = re.split(r"[/.\-]", s)
    day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
    if year < 100:
        year += 2000
    return datetime.date(year, month, day)


def _reconstruct_table_rows(text: str) -> List[List[str]]:
    """
    The translated markdown tables have cell values split across
    multiple lines. Reconstruct complete rows by joining pipe-separated
    fragments until we have a full row.
    """
    lines = text.splitlines()
    rows = []
    current_cells = []
    in_table = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if "|" in stripped:
            # Skip separator rows
            if re.match(r"^\|[\s\-|]+\|$", stripped):
                in_table = True
                continue

            cells = [c.strip() for c in stripped.split("|")]
            # Remove empty first/last from leading/trailing pipes
            if cells and cells[0] == "":
                cells = cells[1:]
            if cells and cells[-1] == "":
                cells = cells[:-1]

            if not in_table and any(c for c in cells if c):
                in_table = True

            if in_table:
                current_cells.extend(cells)

                # Heuristic: a deposit row should have a date-like first cell
                # and enough numeric cells. We collect until we have enough.
                # For Migdal: 6 columns (Date, Salary Month, Salary, Employee, Employer, Total)
                # Filter out empty cells
                non_empty = [c for c in current_cells if c]
                if len(non_empty) >= 6:
                    rows.append(non_empty[:6])
                    current_cells = non_empty[6:]
        else:
            if in_table and current_cells:
                current_cells.append(stripped)
                non_empty = [c for c in current_cells if c]
                if len(non_empty) >= 6:
                    rows.append(non_empty[:6])
                    current_cells = non_empty[6:]

    return rows


def _extract_number_after_label(text: str, label_pattern: str) -> int:
    """Find a number that appears near a label, scanning across line breaks."""
    m = re.search(label_pattern, text, re.IGNORECASE | re.DOTALL)
    if not m:
        return 0
    # Search for the first number after the label match
    rest = text[m.end():]
    num_match = re.search(r"[\-]?\s*([\d,]+)", rest)
    if num_match:
        val = num_match.group(0).replace(" ", "")
        return _parse_number(val)
    return 0


def parse_report(filepath: str) -> ReportData:
    """Parse a translated Migdal Keren Hishtalmut quarterly report."""
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()

    text = _normalize_text(raw)
    # Also create a single-line version for cross-line regex matching
    flat = re.sub(r"\n+", " ", text)

    # --- Period ---
    period_match = re.search(
        r"(?:From\s+date|Period.*?from)\s+(\d{2}/\d{2}/\d{2,4})\s+(?:to\s+date|to)\s+(\d{2}/\d{2}/\d{2,4})",
        flat, re.IGNORECASE
    )
    if not period_match:
        raise ValueError("Could not find report period dates")
    period_start = _parse_date_dmy(period_match.group(1))
    period_end = _parse_date_dmy(period_match.group(2))

    # --- Member Info ---
    member_name = ""
    m = re.search(r"Member\s+Name:\*?\*?\s*(.+?)(?:\s*\*|\s*$)", text, re.IGNORECASE | re.MULTILINE)
    if m:
        member_name = m.group(1).strip().strip("*").strip()

    id_number = ""
    m = re.search(r"ID\s+Number:\*?\*?\s*(.+?)(?:\s*\*|\s*$)", text, re.IGNORECASE | re.MULTILINE)
    if m:
        id_number = m.group(1).strip().strip("*").strip()

    account_number = ""
    m = re.search(r"Account\s+Number:\*?\*?\s*(.+?)(?:\s*\*|\s*$)", text, re.IGNORECASE | re.MULTILINE)
    if m:
        account_number = m.group(1).strip().strip("*").strip()

    employer = ""
    m = re.search(r"Employer\s+Name:\*?\*?\s*(.+?)(?:\s*\*|\s*$)", text, re.IGNORECASE | re.MULTILINE)
    if m:
        employer = m.group(1).strip().strip("*").strip()

    # --- Fund name from header ---
    fund_name = "Migdal Keren Hishtalmut"
    m = re.search(r"(?:Quarterly\s+Report.*?in|Report.*?member.*?in)\s+(.+?)\s+for\s+the\s+end", flat, re.IGNORECASE)
    if m:
        fund_name = m.group(1).strip().strip("*").strip()

    # --- Section B: Movements ---
    # Extract Section B specifically to avoid matching in other sections.
    # Use \n---\n (not just ---) to avoid matching table separator rows like | --- |
    section_b = re.search(
        r"(?:B\.\s*Movements|Movements\s+in\s+(?:Your\s+Account|the\s+Pension))(.*?)(?:\n---\n|\nC\.\s|Management\s+Fees?\s+Percentage)",
        text, re.IGNORECASE | re.DOTALL
    )
    section_b_flat = re.sub(r"\n+", " ", section_b.group(1)) if section_b else flat

    opening_balance = _extract_number_after_label(
        section_b_flat, r"Balance\s+of\s+funds\s+(?:in\s+the\s+account\s+)?at\s+the\s+beginning"
    )

    total_deposits = _extract_number_after_label(
        section_b_flat, r"(?:Funds\s+deposited|Deposits\s+made)"
    )

    reported_profit = _extract_number_after_label(
        section_b_flat, r"Profits?\s+(?:less|after)\s+investment\s+management\s+expenses"
    )

    management_fees = abs(_extract_number_after_label(
        section_b_flat, r"Management\s+fees\s+(?:collected|charged)"
    ))

    ending_balance = 0
    # Find "Balance ... as of DD/MM/YYYY" within Section B, then grab the number
    m = re.search(r"Balance.*?as\s+of.*?(\d{2}/\d{2}/\d{4})", section_b_flat, re.IGNORECASE)
    if m:
        rest = section_b_flat[m.end():]
        nums = re.findall(r"([\d,]+)", rest[:200])
        for n in nums:
            val = _parse_number(n)
            if val > 1000:
                ending_balance = val
                break
    if ending_balance == 0:
        # Fallback: last large number in section B
        nums = re.findall(r"([\d,]+)", section_b_flat)
        for n in reversed(nums):
            val = _parse_number(n)
            if val > 10000:
                ending_balance = val
                break

    # --- Section C: Fee rates ---
    mgmt_fee_savings_pct = 0.0
    m = re.search(r"Management\s+fees?\s+from\s+savings:\*?\*?\s*\*?\*?\s*([\d.]+)\s*%", flat, re.IGNORECASE)
    if m:
        mgmt_fee_savings_pct = float(m.group(1))

    mgmt_fee_deposits_pct = 0.0
    m = re.search(r"Management\s+fees?\s+from\s+deposits:\*?\*?\s*\*?\*?\s*([\d.]+)\s*%", flat, re.IGNORECASE)
    if m:
        mgmt_fee_deposits_pct = float(m.group(1))

    # --- Section D: Track and return ---
    track_name = ""
    m = re.search(r"\*?\*?Track:\*?\*?\s*(.+?)(?:\n|$)", text, re.IGNORECASE)
    if m:
        track_name = m.group(1).strip().strip("*").strip()

    reported_track_return_pct = 0.0
    m = re.search(r"Return\s+during\s+the\s+reporting\s+period.*?:\*?\*?\s*\*?\*?\s*([\d.]+)\s*%", flat, re.IGNORECASE)
    if m:
        reported_track_return_pct = float(m.group(1))

    # --- Section E: Deposits table ---
    deposits = []
    section_e = re.search(
        r"(?:Details\s+of\s+Deposits|E\.\s+Details\s+of\s+Deposits|E\.\s+Detailed\s+Deposits)(.*?)(?:\n---\n|\nF\.|Details\s+of\s+Your\s+Agent|Agent.*?Advisor|\Z)",
        text, re.IGNORECASE | re.DOTALL
    )
    if section_e:
        section_text = section_e.group(1)
        # Merge pipe-separated cells that span multiple lines into single rows.
        # Each table row starts with "| DD/MM/YYYY" and ends before the next date.
        # Collect all pipe-delimited values into a stream, then chunk by dates.
        all_cells = []
        for line in section_text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("| ---"):
                continue
            # Split by pipe and gather non-empty cells
            if "|" in stripped:
                parts = [p.strip() for p in stripped.split("|")]
                for p in parts:
                    clean = re.sub(r"<[^>]+>", "", p).strip().strip("*").strip()
                    if clean:
                        all_cells.append(clean)

        # Now scan through cells to find deposit rows
        # A deposit row starts with DD/MM/YYYY and has 5 more values
        i = 0
        while i < len(all_cells):
            cell = all_cells[i]
            if re.match(r"\d{2}/\d{2}/\d{4}$", cell):
                # Potential deposit row - grab next 5 cells
                if i + 5 < len(all_cells):
                    try:
                        dep = Deposit(
                            date=_parse_date_dmy(cell),
                            salary_month=all_cells[i + 1],
                            salary=_parse_number(all_cells[i + 2]),
                            employee=_parse_number(all_cells[i + 3]),
                            employer=_parse_number(all_cells[i + 4]),
                            total=_parse_number(all_cells[i + 5]),
                        )
                        deposits.append(dep)
                        i += 6
                        continue
                    except (ValueError, IndexError):
                        pass
            i += 1

    return ReportData(
        period_start=period_start,
        period_end=period_end,
        member_name=member_name,
        id_number=id_number,
        account_number=account_number,
        employer=employer,
        fund_name=fund_name,
        track_name=track_name,
        opening_balance=opening_balance,
        total_deposits=total_deposits,
        reported_profit=reported_profit,
        management_fees=management_fees,
        ending_balance=ending_balance,
        mgmt_fee_savings_pct=mgmt_fee_savings_pct,
        mgmt_fee_deposits_pct=mgmt_fee_deposits_pct,
        reported_track_return_pct=reported_track_return_pct,
        deposits=deposits,
    )
