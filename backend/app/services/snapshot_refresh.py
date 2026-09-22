from app.engines.amortization import equal_payment_schedule
from app.repositories import loans, runs


def recompute_with_loan_rate(conn, row: dict) -> dict:
    payload = __import__("json").loads(row.get("input_json") or "{}")
    principal = float(payload["principal"])
    months = int(payload["months"])
    annual_rate = float(payload["annual_rate"])
    loan_id = row.get("loan_id")
    if loan_id is not None:
        loan = loans.get(conn, loan_id)
        if loan and loan.get("annual_rate") is not None:
            annual_rate = float(loan["annual_rate"])
    full = equal_payment_schedule(principal, annual_rate, months)
    out = {k: full[k] for k in ("monthly_payment", "total_interest", "total_payment")}
    out["preview"] = full["rows"][: min(12, len(full["rows"]))]
    out["row_count"] = len(full["rows"])
    return out


def write_through(conn, run_id: int, out: dict) -> None:
    runs.replace_result(conn, run_id, out)


def touch_latest_run_for_loan(conn, loan_id: int, out: dict) -> None:
    row = conn.execute(
        "SELECT id FROM calc_runs WHERE loan_id=? ORDER BY id DESC LIMIT 1",
        (loan_id,),
    ).fetchone()
    if row:
        write_through(conn, int(row["id"]), out)
