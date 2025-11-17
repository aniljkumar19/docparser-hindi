# /app/scripts/eval_parsers.py  (copy-paste whole file)
import os, argparse, csv, sys
sys.path.insert(0, "/app")  # ensure 'app' package import works inside container
from app.parsers.router import parse_any

KEYS = ["detected_type", "date", "total", "amount_due", "items"]

def load_expected(base: str):
    exp = {}
    path = os.path.join(base, "expected.csv")
    if not os.path.exists(path):
        return exp
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            exp[row["file"]] = row
    return exp

def _norm(s):
    return ("" if s is None else str(s)).strip()

def _num_or_none(s):
    try:
        return round(float(str(s).replace(",", "").strip()), 2)
    except Exception:
        return None

def _match_field(exp, got, *, numeric=False, integer=False, casefold=False):
    exp = _norm(exp)
    got = _norm(got)
    if exp == "":  # blank expected = wildcard (don’t check)
        return True
    if numeric:
        return _num_or_none(exp) == _num_or_none(got)
    if integer:
        return (got.isdigit() and exp.isdigit() and int(got) == int(exp))
    if casefold:
        return got.lower() == exp.lower()
    return got == exp

def main():
    p = argparse.ArgumentParser()
    p.add_argument("path", help="File or directory of samples")
    args = p.parse_args()

    base = args.path
    files = []
    if os.path.isdir(base):
        for f in sorted(os.listdir(base)):
            fp = os.path.join(base, f)
            if os.path.isfile(fp) and f != "expected.csv":
                files.append(fp)
    else:
        files = [base]
        base = os.path.dirname(base) or "."

    expected = load_expected(base)

    print("file,detected_type,date,total,amount_due,items,ok")
    ok_total = 0

    for fp in files:
        name = os.path.basename(fp)
        with open(fp, "rb") as fh:
            data = fh.read()

        result, meta = parse_any(name, data)

        dtype = (meta or {}).get("detected_doc_type") or ""
        date  = (result or {}).get("date")
        if isinstance(date, dict):
            date = date.get("value")
        total = (result or {}).get("total")
        amt   = (result or {}).get("amount_due")
        items = len((result or {}).get("line_items") or [])

        row = {
            "file": name,
            "detected_type": dtype,
            "date": "" if date is None else str(date),
            "total": "" if total is None else str(total),
            "amount_due": "" if amt is None else str(amt),
            "items": str(items),
        }

        exp_row = expected.get(name)
        is_ok = ""
        if exp_row:
            same_type  = _match_field(exp_row.get("detected_type"), row["detected_type"], casefold=True)
            same_date  = _match_field(exp_row.get("date"),          row["date"])
            same_total = _match_field(exp_row.get("total"),         row["total"], numeric=True)
            same_amt   = _match_field(exp_row.get("amount_due"),    row["amount_due"], numeric=True)
            same_items = _match_field(exp_row.get("items"),         row["items"], integer=True)
            is_ok = "pass" if (same_type and same_date and same_total and same_amt and same_items) else "FAIL"
            if is_ok == "pass":
                ok_total += 1

        print("{file},{detected_type},{date},{total},{amount_due},{items},{ok}".format(ok=is_ok, **row))

    if expected:
        print(f"Summary: {ok_total}/{len(expected)} passing")

if __name__ == "__main__":
    main()
