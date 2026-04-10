"""
scripts/generate_demo_pdf.py
─────────────────────────────────────────────────────────────────────────────
Generates sample RBI-style regulatory circular PDFs for demo purposes.
Creates both a "new" and an "old" version to demonstrate diff detection.

Usage:
    python scripts/generate_demo_pdf.py
─────────────────────────────────────────────────────────────────────────────
"""

import os
from pathlib import Path

# We use reportlab if available, else fallback to fitz (PyMuPDF)
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    USE_REPORTLAB = True
except ImportError:
    USE_REPORTLAB = False

import fitz  # PyMuPDF — always available

DEMO_DIR = Path("./data/demo")
DEMO_DIR.mkdir(parents=True, exist_ok=True)


NEW_CIRCULAR_TEXT = """RESERVE BANK OF INDIA
Department of Regulation
Central Office, Mumbai – 400 001

RBI/2024-25/117
DOR.CAP.REC.85/21.06.201/2024-25

April 5, 2025

All Scheduled Commercial Banks
(Excluding Regional Rural Banks and Small Finance Banks)

Dear Sir/Madam,

Master Circular - Prudential Norms on Capital Adequacy - Basel III Framework
(Revised April 2025)

1. BACKGROUND
The Reserve Bank of India has been progressively implementing the Basel III capital adequacy framework since April 2013. In light of recent global banking developments and recommendations from the Basel Committee on Banking Supervision (BCBS), the following revised guidelines are issued with immediate effect.

2. MINIMUM CAPITAL REQUIREMENTS (REVISED)
2.1 Common Equity Tier 1 (CET1): Minimum ratio increased to 6.0% of Risk Weighted Assets (RWAs) from the existing 5.5%.
2.2 Total Tier 1 Capital: Minimum ratio revised to 8.5% of RWAs.
2.3 Total Capital Adequacy Ratio (CRAR): Minimum maintained at 11.5% inclusive of Capital Conservation Buffer.
2.4 Capital Conservation Buffer (CCB): Maintained at 2.5% of RWAs as per current norms.
2.5 Countercyclical Capital Buffer (CCyB): Activated at 0.5% of RWAs effective June 30, 2025. Banks are required to hold this additional buffer immediately.

3. LEVERAGE RATIO
3.1 Minimum leverage ratio increased to 4.5% (from existing 4%) for Domestic Systemically Important Banks (D-SIBs).
3.2 Non-D-SIB banks must maintain leverage ratio of 3.5% (unchanged).
3.3 Leverage ratio disclosure is MANDATORY in quarterly financial results.

4. INTEREST RATE RISK IN BANKING BOOK (IRRBB)
4.1 All banks with a balance sheet size above ₹50,000 crore must implement an advanced IRRBB model by December 31, 2025.
4.2 Earnings at Risk (EaR) limit: Maximum 15% of Net Interest Income (NII).
4.3 Economic Value of Equity (EVE) sensitivity: Revised maximum to 10% of Tier 1 Capital (previously 15%).

5. LIQUIDITY REQUIREMENTS
5.1 Liquidity Coverage Ratio (LCR): Minimum maintained at 100%. Banks must build a 5% buffer above the minimum.
5.2 Net Stable Funding Ratio (NSFR): Minimum remains 100% with enhanced monitoring for banks below 110%.
5.3 Daily LCR monitoring is mandatory for all banks with assets exceeding ₹10,000 crore.

6. CLIMATE RISK CAPITAL ADD-ON
6.1 With effect from April 1, 2026, banks must maintain a Climate Risk Capital Add-on equivalent to 0.5% of RWAs if their financed emissions in high-carbon sectors exceed 30% of total corporate loan book.
6.2 Banks must disclose climate-related risk exposure in compliance with the Task Force on Climate-related Financial Disclosures (TCFD) framework by December 2025.

7. CYBERSECURITY CAPITAL REQUIREMENT (NEW)
7.1 Banks that have experienced a material cyber incident (as defined by RBI Cyber Security Framework 2021) in the previous 24 months must maintain an operational risk add-on of 0.25% of RWAs.
7.2 Self-certification of compliance must be submitted to the Department of Regulation annually.

8. REPORTING AND DISCLOSURE
8.1 Capital adequacy returns (CAR Return) must be submitted within 21 days of quarter-end (revised from 30 days).
8.2 All pillar 3 disclosures must now be published within 45 days of quarter-end on the bank's official website.
8.3 Non-compliance with reporting timelines will attract a penalty of ₹5 lakh per day of delay.

9. TRANSITIONAL ARRANGEMENTS
Banks currently below the revised CET1 minimum of 6.0% must submit a Board-approved Capital Restoration Plan to RBI within 90 days of this circular. No dividend distribution is permitted until the CET1 minimum is met.

10. EFFECTIVE DATE
These guidelines come into force with immediate effect unless a specific effective date is mentioned. All banks must ensure compliance by June 30, 2025, unless otherwise stated.

Yours faithfully,

(N. Kumar)
Chief General Manager

Enclosure: Revised Annex on Capital Instruments Eligibility Criteria
"""


OLD_CIRCULAR_TEXT = """RESERVE BANK OF INDIA
Department of Regulation
Central Office, Mumbai – 400 001

RBI/2023-24/98
DOR.CAP.REC.72/21.06.201/2023-24

March 12, 2024

All Scheduled Commercial Banks
(Excluding Regional Rural Banks and Small Finance Banks)

Dear Sir/Madam,

Master Circular - Prudential Norms on Capital Adequacy - Basel III Framework

1. BACKGROUND
The Reserve Bank of India has been implementing the Basel III capital adequacy framework since April 2013. The following guidelines consolidate all instructions issued in this regard.

2. MINIMUM CAPITAL REQUIREMENTS
2.1 Common Equity Tier 1 (CET1): Minimum ratio of 5.5% of Risk Weighted Assets (RWAs).
2.2 Total Tier 1 Capital: Minimum ratio of 7.0% of RWAs.
2.3 Total Capital Adequacy Ratio (CRAR): Minimum of 11.5% inclusive of Capital Conservation Buffer.
2.4 Capital Conservation Buffer (CCB): 2.5% of RWAs.
2.5 Countercyclical Capital Buffer (CCyB): Currently deactivated (0%).

3. LEVERAGE RATIO
3.1 Minimum leverage ratio for D-SIBs: 4.0%.
3.2 Non-D-SIB banks: 3.5%.
3.3 Leverage ratio disclosure on a quarterly basis.

4. INTEREST RATE RISK IN BANKING BOOK (IRRBB)
4.1 Banks are encouraged to implement advanced IRRBB models.
4.2 Earnings at Risk (EaR) limit: Maximum 15% of Net Interest Income (NII).
4.3 Economic Value of Equity (EVE) sensitivity: Maximum 15% of Tier 1 Capital.

5. LIQUIDITY REQUIREMENTS
5.1 Liquidity Coverage Ratio (LCR): Minimum 100%.
5.2 Net Stable Funding Ratio (NSFR): Minimum 100%.
5.3 Monthly LCR monitoring for banks with assets below ₹10,000 crore.

6. REPORTING AND DISCLOSURE
6.1 Capital adequacy returns (CAR Return) must be submitted within 30 days of quarter-end.
6.2 All pillar 3 disclosures must be published within 60 days of quarter-end.
6.3 Non-compliance with timelines will attract regulatory action as deemed appropriate.

7. EFFECTIVE DATE
These guidelines are effective from April 1, 2024.

Yours faithfully,

(R. Sharma)
Chief General Manager
"""


def _write_pdf_with_fitz(text: str, path: Path):
    """Create a simple PDF using PyMuPDF."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4

    # Write text block
    rect = fitz.Rect(50, 50, 545, 800)
    page.insert_textbox(
        rect,
        text,
        fontsize=9,
        fontname="helv",
        color=(0, 0, 0),
    )

    doc.save(str(path))
    doc.close()
    print(f"[DemoGen] ✅  Created: {path}")


def generate():
    new_path = DEMO_DIR / "rbi_circular_2025_new.pdf"
    old_path = DEMO_DIR / "rbi_circular_2024_old.pdf"

    _write_pdf_with_fitz(NEW_CIRCULAR_TEXT, new_path)
    _write_pdf_with_fitz(OLD_CIRCULAR_TEXT, old_path)

    print(f"\n📄 Demo PDFs ready:")
    print(f"   NEW: {new_path}")
    print(f"   OLD: {old_path}")
    print("\nUpload these via the web UI or API:")
    print("  curl -X POST http://localhost:8000/upload \\")
    print(f"    -F 'new_pdf=@{new_path}' \\")
    print(f"    -F 'old_pdf=@{old_path}'")


if __name__ == "__main__":
    generate()
