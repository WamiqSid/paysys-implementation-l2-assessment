# INCIDENT-001 – Intermittent Transaction Search Failure

**Priority:** P2  
**Service:** MiniPay API `GET /api/search`  
**Status:** Closed – defect introduced, reproduced, fixed, and covered by regression tests

## Observations
Client operations reported HTTP 500 on some transaction searches while neighbouring IDs succeeded. Failures were intermittent from the operator’s point of view: the same UI action worked or failed depending on the reference typed.

## Reproduction
The schema does **not** enforce uniqueness on `transactions.transaction_ref`. `database/generate_data.py` plants collisions on purpose:

```python
ref_num = i if i % 5000 else i - 1
```

So `TXN00004999` exists twice (rows 4999 and 5000), `TXN00009999` twice, and so on.

To demonstrate a realistic code defect rather than a theoretical one, MiniPay was first shipped with:

```python
# buggy path: assumes one row per ref
return [db.scalars(stmt).unique().one()]
```

Enable with `BUGGY_SEARCH=true` (kept only as a reproduction flag).

```bash
BUGGY_SEARCH=true python -m uvicorn app.main:app --port 8080
curl -H "X-API-Key: minipay-dev-key" "http://127.0.0.1:8080/api/search?q=TXN-DUP"
# HTTP 500  {"detail":"Internal server error","code":"DUPLICATE_REF_LOOKUP"}
```

Automated proof: `tests/api/test_api.py::test_buggy_search_returns_500_on_duplicates`.

## Evidence
- SQLAlchemy `MultipleResultsFound` when `.one()` sees two rows.
- FastAPI exception handler logs `transaction search returned multiple rows`.
- Unique refs (`TXN-OK`) still returned 200 while duplicates returned 500 — matches the ticket.
- `sql/04_duplicate_refs.sql` lists the colliding refs in the 50k seed.

## Hypotheses considered

| Hypothesis | Result |
|---|---|
| Database connectivity blips | Rejected: `/health` stayed 200 while search 500’d |
| Invalid input / injection | Rejected: only certain *valid* refs failed |
| Missing row / 404 mapped to 500 | Rejected: unknown refs are empty 200; the 500 required *multiple* rows |
| Non-unique `transaction_ref` + `.one()` | **Confirmed** |

## Root cause
The search handler treated `transaction_ref` as a unique business key. It is not unique in the schema or in production-like seed data. Duplicate refs made `.one()` raise; the unhandled ORM error became HTTP 500.

## Immediate corrective action
1. Stop using `.one()` for this lookup. Load `all()` / `scalars().all()`.
2. Return HTTP 200 with `duplicate_ref: true` and every matching row so L2 can see the clash instead of an empty error page.
3. Keep `BUGGY_SEARCH` default **false**.

## Permanent corrective / preventive action
1. Data cleanup of duplicate refs (keep the row that has a SUCCESS callback, re-key the other).
2. After cleanup, add `UNIQUE (transaction_ref)` — not before, or seed/reload fails.
3. Regression test `test_duplicate_search_is_safe_by_default`.
4. Support CLI flags duplicate refs as `DUPLICATE_TRANSACTION_REF` (exit code 2).

## Validation
```bash
python -m pytest tests/api/test_api.py::test_duplicate_search_is_safe_by_default tests/api/test_api.py::test_buggy_search_returns_500_on_duplicates -q
```

Default search of a colliding ref now returns 200 and `count >= 2`. The flagged buggy path still returns 500, proving the original failure mode.
