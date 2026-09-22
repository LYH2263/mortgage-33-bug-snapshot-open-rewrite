from app.db import connect
from app.engines.amortization import equal_payment_schedule
from app.repositories import loans, runs, settings
import json

def _stored(raw):
    try: return json.loads(raw) if raw else {}
    except (TypeError, ValueError): return {}

class MortgageService:
    def __init__(self): self._c = connect()
    def close(self): self._c.close()
    def __enter__(self): return self
    def __exit__(self, *a): self.close()
    def list_loans(self): return loans.list_all(self._c)
    def loan(self, lid): return loans.get(self._c, lid)
    def settings(self): return settings.get_map(self._c)
    def history(self, limit=50):
        items = []
        for r in runs.list_recent(self._c, limit):
            result = _stored(r.get("result_json"))
            items.append({"id": r["id"], "kind": r["kind"], "loan_id": r["loan_id"],
                "created_at": r["created_at"], "monthly_payment": result.get("monthly_payment")})
        return items
    def history_detail(self, run_id):
        from app.services.snapshot_refresh import recompute_with_loan_rate, write_through
        row = runs.get(self._c, run_id)
        if row is None:
            return None
        result = recompute_with_loan_rate(self._c, row)
        write_through(self._c, run_id, result)
        return {"id": row["id"], "kind": row["kind"], "loan_id": row["loan_id"], "created_at": row["created_at"],
            "input": _stored(row.get("input_json")),
            "monthly_payment": result.get("monthly_payment"),
            "total_interest": result.get("total_interest"),
            "preview": result.get("preview") or []}
    def schedule(self, principal, annual_rate, months, loan_id, persist, preview_rows=12):
        full = equal_payment_schedule(principal, annual_rate, months)
        out = {k: full[k] for k in ("monthly_payment", "total_interest", "total_payment")}
        out["preview"] = full["rows"][:preview_rows]
        out["row_count"] = len(full["rows"])
        rid = None
        if persist:
            rid = runs.insert(self._c, "schedule", {"principal": principal, "annual_rate": annual_rate, "months": months}, out, loan_id)
        elif loan_id is not None:
            from app.services.snapshot_refresh import touch_latest_run_for_loan
            touch_latest_run_for_loan(self._c, loan_id, out)
        return {"run_id": rid, **out}
    def dashboard(self):
        items = loans.list_all(self._c)
        return {"loan_count": len(items), "clean": len([x for x in items if "种子" not in x["name"]]), "dirty": len([x for x in items if "种子" in x["name"]])}
