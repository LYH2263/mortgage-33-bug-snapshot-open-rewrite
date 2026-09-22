import os, tempfile
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="mortgage-test-")

from app import seed
from app.db import connect
from app.engines.amortization import equal_payment_schedule
from app.repositories import runs
from app.services.mortgage_service import MortgageService

def _svc():
    seed.init_db()
    return MortgageService()

def _count(conn):
    return conn.execute("SELECT COUNT(*) c FROM calc_runs").fetchone()["c"]

def test_detail_returns_pinned_snapshot():
    s = _svc()
    rid = s.schedule(1_000_000, 3.5, 360, None, True)["run_id"]
    s.schedule(500_000, 6.0, 120, None, True)
    exp = equal_payment_schedule(1_000_000, 3.5, 360)
    d = s.history_detail(rid)
    assert d["id"] == rid
    assert d["input"] == {"principal": 1_000_000, "annual_rate": 3.5, "months": 360}
    assert d["monthly_payment"] == exp["monthly_payment"]
    assert d["total_interest"] == exp["total_interest"]
    assert d["preview"] == exp["rows"][:12]
    s.close()

def test_detail_ignores_current_loan_params():
    s = _svc()
    rid = s.schedule(1_000_000, 3.5, 360, None, True)["run_id"]
    before = s.history_detail(rid)
    conn = connect()
    conn.execute("UPDATE loans SET principal=1, annual_rate=99, months=1")
    conn.commit(); conn.close()
    after = s.history_detail(rid)
    assert after == before
    assert after["monthly_payment"] == 4490.45
    s.close()

def test_missing_run_returns_none_and_writes_nothing():
    s = _svc()
    conn = connect()
    before = _count(conn)
    assert s.history_detail(999999) is None
    assert _count(conn) == before
    conn.close(); s.close()

def test_list_summary_comes_from_store():
    s = _svc()
    conn = connect()
    rid = runs.insert(conn, "schedule",
        {"principal": 1_000_000, "annual_rate": 3.5, "months": 360},
        {"monthly_payment": 0.01, "total_interest": 0.02, "preview": []})
    conn.close()
    item = [x for x in s.history() if x["id"] == rid][0]
    assert item["monthly_payment"] == 0.01
    s.close()

def test_rerun_inserts_new_record_without_touching_old():
    s = _svc()
    rid = s.schedule(1_000_000, 3.5, 360, None, True)["run_id"]
    before = s.history_detail(rid)
    conn = connect()
    n = _count(conn)
    rid2 = s.schedule(800_000, 4.2, 240, None, True)["run_id"]
    assert rid2 != rid
    assert _count(conn) == n + 1
    assert s.history_detail(rid) == before
    conn.close(); s.close()
