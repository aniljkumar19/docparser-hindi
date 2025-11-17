import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.parsers.policy_loader import load_policy, pick_bank_profile


def test_profile_picker_generic():
    cfg = load_policy()
    prof = pick_bank_profile("Welcome to Sample Bank Statement", cfg)
    assert prof.name == "generic"
    assert "interest_minor_amount" in prof.tx_rules


def test_profile_picker_hdfc():
    cfg = load_policy()
    text = "HDFC BANK LTD IFSC: HDFC0001234"
    prof = pick_bank_profile(text, cfg)
    assert prof.name == "HDFC"
    assert "join_neft_ref" in prof.tx_rules

