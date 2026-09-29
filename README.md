# Roth IRA / Keren Hishtalmut return verifier

Verifies Israeli **Keren Hishtalmut** (study fund) quarterly returns against public market data. It parses an English translation of your fund report, pulls index and FX series from Yahoo Finance, and writes an HTML summary plus an Excel workbook.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

Place your translated quarterly report locally (not committed — see `.gitignore`). Then:

```bash
python3 verify.py path/to/translated-report.md
# or
python3 -m roth_ira_verifier path/to/translated-report.md
```

Outputs (gitignored):

- `output/report.html`
- `output/analysis.xlsx`

## Project layout

| Path | Role |
|------|------|
| `verify.py` | CLI wrapper |
| `roth_ira_verifier/parser.py` | Parse translated report text |
| `roth_ira_verifier/market_data.py` | Yahoo Finance data |
| `roth_ira_verifier/calculator.py` | Expected returns and balance simulation |
| `roth_ira_verifier/report_generator.py` | HTML report |
| `roth_ira_verifier/excel_export.py` | Excel export |

## Input format

The parser expects English translations of Migdal-style quarterly member reports (Gemini/GPT translations of the Hebrew PDF). Keep originals and translations in a local `reports/` folder.
