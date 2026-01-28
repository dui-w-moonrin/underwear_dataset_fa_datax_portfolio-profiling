import csv
import math
from pathlib import Path

SRC = Path("artifacts/scorecard.csv")
DST = Path("artifacts/scorecard_100.csv")

def to_float(x, default=0.0):
    try:
        if x is None:
            return default
        s = str(x).strip()
        if s == "" or s.lower() == "null" or s.lower() == "nan":
            return default
        return float(s)
    except Exception:
        return default

def to_int(x, default=0):
    try:
        if x is None:
            return default
        s = str(x).strip()
        if s == "" or s.lower() == "null" or s.lower() == "nan":
            return default
        # some columns may look like "17606.0"
        return int(float(s))
    except Exception:
        return default

def compute_score(row):
    # Inputs (these are percent 0..100 in your current scorecard.csv)
    overall_null_pct = to_float(row.get("overall_null_pct", 0.0), 0.0)
    pk_null_pct      = to_float(row.get("pk_null_pct", 0.0), 0.0)

    pk_duplicate_rows = to_int(row.get("pk_duplicate_rows", 0), 0)
    neg_value_flags   = to_float(row.get("neg_value_flags", 0.0), 0.0)

    fk_orphan_rows = to_float(row.get("fk_orphan_rows", 0.0), 0.0)
    row_count      = to_float(row.get("row_count", 0.0), 0.0)

    date_min = (row.get("date_min", "") or "").strip()
    date_max = (row.get("date_max", "") or "").strip()

    score = 100.0

    # A) Completeness
    score -= min(30.0, overall_null_pct * 0.8)

    # B) PK health
    score -= min(30.0, pk_null_pct * 2.0)

    if pk_duplicate_rows > 0:
        score -= min(30.0, 10.0 + math.log10(pk_duplicate_rows + 1.0) * 10.0)

    # C) Negative flags
    if neg_value_flags > 0:
        score -= min(20.0, neg_value_flags * 5.0)

    # D) FK orphan ratio penalty
    if fk_orphan_rows > 0 and row_count > 0:
        orphan_ratio = fk_orphan_rows / row_count
        score -= min(40.0, orphan_ratio * 40.0)

    # E) Date usability (soft)
    has_min = len(date_min) > 0
    has_max = len(date_max) > 0
    if has_min ^ has_max:
        score -= 5.0

    # clamp 0..100
    score = max(0.0, min(100.0, score))
    return int(round(score))

def main():
    if not SRC.exists():
        raise FileNotFoundError(f"Missing {SRC}. Run scorecard generation first.")

    with SRC.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    # We will output columns with updated_at replaced by dq_score_0_100
    out_fields = []
    for fn in fieldnames:
        if fn == "updated_at":
            out_fields.append("dq_score_0_100")
        else:
            out_fields.append(fn)

    for r in rows:
        r["dq_score_0_100"] = str(compute_score(r))

    DST.parent.mkdir(parents=True, exist_ok=True)
    with DST.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        for r in rows:
            out_row = {}
            for fn in fieldnames:
                if fn == "updated_at":
                    out_row["dq_score_0_100"] = r["dq_score_0_100"]
                else:
                    out_row[fn] = r.get(fn, "")
            writer.writerow(out_row)

    print(f"OK: wrote {DST}")

if __name__ == "__main__":
    main()