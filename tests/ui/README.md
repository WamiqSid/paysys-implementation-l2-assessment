# GUI test automation

```bash
cd tests/ui
npm install
npx playwright install chromium
npx playwright test
```

This is the documented command for the complete UI suite. HTML output is written to `tests/ui/playwright-report/`.

If the API is already running:

```bash
set MINIPAY_BASE_URL=http://127.0.0.1:8080
npx playwright test
```

Selectors use `data-testid` attributes (`login-key`, `search-input`, `payment-submit`, …) rather than sleeps.

## CI split
- **Every pull request / every release candidate:** this Playwright smoke file (sign-in, create payment, search, negative amount, bad API key). Fast, stable, high signal.
- **Nightly / pre-production regression:** add multi-browser, longer search cases against a 50k-row seed, and visual snapshots. Do not block every commit on the full set.
