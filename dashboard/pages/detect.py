import re

KEYS = {
  "invoice": [r"\binvoice\b", r"\bsubtotal\b", r"\btotal\b", r"\bgstin\b", r"\btax invoice\b"],
  "birth_certificate": [r"\bbirth certificate\b", r"\bdate of birth\b", r"\bplace of birth\b"],
}
def detect_doc_type(text: str) -> str:
  scores = {k: 0 for k in KEYS}
  low = text.lower()
  for t, pats in KEYS.items():
    for p in pats:
      if re.search(p, low): scores[t] += 1
  # pick the best nonzero match, else unknown
  best = max(scores, key=scores.get)
  return best if scores[best] > 0 else "unknown"
