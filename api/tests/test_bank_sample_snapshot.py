from app.parsers.bank_normalizer import normalize_bank_statement
from app.parsers.policy_loader import ParserPolicy


SAMPLE_TRANSACTIONS = [
    {"date": "10/02", "description": "POS PURCHASE", "debit": 4.23, "credit": 0.0, "balance": 65.73, "channel": "POS"},
    {"date": "10/03", "description": "PREAUTHORIZED CREDIT", "debit": 0.0, "credit": 763.01, "balance": 828.74},
    {"date": "10/04", "description": "POS PURCHASE", "debit": 11.68, "credit": 0.0, "balance": 817.06, "channel": "POS"},
    {"date": "10/05", "description": "CHECK 1234", "debit": 9.98, "credit": 0.0, "balance": 807.08},
    {"date": "10/05", "description": "POS PURCHASE", "debit": 25.50, "credit": 0.0, "balance": 781.58, "channel": "POS"},
    {"date": "10/08", "description": "POS PURCHASE", "debit": 59.08, "credit": 0.0, "balance": 722.50, "channel": "POS"},
    {"date": "10/12", "description": "CHECK 1236", "debit": 69.00, "credit": 0.0, "balance": 653.50},
    {"date": "10/14", "description": "CHECK 1237", "debit": 180.63, "credit": 0.0, "balance": 472.87},
    {"date": "10/14", "description": "POS PURCHASE", "debit": 18.96, "credit": 0.0, "balance": 453.91, "channel": "POS"},
    {"date": "10/16", "description": "PREAUTHORIZED CREDIT", "debit": 0.0, "credit": 763.01, "balance": 1216.92},
    {"date": "10/22", "description": "ATM WITHDRAWAL", "debit": 140.00, "credit": 0.0, "balance": 1076.92, "channel": "ATM"},
    {"date": "10/28", "description": "CHECK 1238", "debit": 91.06, "credit": 0.0, "balance": 985.86},
    {"date": "10/30", "description": "CHECK 1239", "debit": 451.20, "credit": 0.0, "balance": 534.66},
    {"date": "10/30", "description": "CHECK 1246", "debit": 37.07, "credit": 0.0, "balance": 497.59},
    {"date": "10/30", "description": "POS PURCHASE", "debit": 18.67, "credit": 0.0, "balance": 478.92, "channel": "POS"},
    {"date": "10/31", "description": "CHECK 1247", "debit": 100.00, "credit": 0.0, "balance": 378.92},
    {"date": "10/31", "description": "CHECK 1248", "debit": 78.24, "credit": 0.0, "balance": 300.68},
    {"date": "10/31", "description": "PREAUTHORIZED CREDIT", "debit": 0.0, "credit": 350.00, "balance": 650.68},
    {"date": "11/02", "description": "CHECK 1249 §", "debit": 52.23, "credit": 0.0, "balance": 598.45},
    {"date": "11/09", "description": "INTEREST CREDIT", "debit": 0.0, "credit": 0.26, "balance": 598.71},
    {"date": "11/09", "description": "SERVICE CHARGE", "debit": 12.00, "credit": 0.0, "balance": 586.71},
]


def test_sample_bank_statement_metrics():
    profile = ParserPolicy(
        name="generic",
        residual_tolerance=1.0,
        tx_rules=["interest_minor_amount", "fix_check_plus_50"],
    )
    normalized = normalize_bank_statement(
        ocr_text="Statement period October 10 2025 to November 9 2025",
        transactions=SAMPLE_TRANSACTIONS,
        opening_balance=69.96,
        closing_balance=586.71,
        profile=profile,
    )

    assert normalized.reconciliation_rate == 1.0
    assert normalized.closing_drift == 0.0
    assert normalized.totals["count"] == len(SAMPLE_TRANSACTIONS)
    assert normalized.period_start == "2025-10-10"
    assert normalized.period_end == "2025-11-09"

    check_1249 = normalized.transactions[18]
    assert check_1249["description"] == "CHECK 1249 5"
    assert check_1249.get("channel") == "CHECK"

