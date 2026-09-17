# GUI test run

Command:

```bash
cd tests/ui
npx playwright test
```

Result (this submission):

```text
Running 2 tests using 1 worker
  ok 1 tests\journeys.spec.js:11:1 › sign-in, create payment, search, and reject invalid amount (2.2s)
  ok 2 tests\journeys.spec.js:44:1 › invalid API key is rejected (682ms)
  2 passed (9.8s)
```

Journeys covered: operator sign-in, create payment, search by reference, successful result, rejected amount `13.13`, invalid API key. HTML report directory (local, gitignored): `tests/ui/playwright-report/`.
