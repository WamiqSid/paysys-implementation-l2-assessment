const { test, expect } = require("@playwright/test");

const API_KEY = process.env.MINIPAY_API_KEY || "minipay-dev-key";

async function signIn(page, key = API_KEY) {
  await page.goto("/");
  await page.getByTestId("login-key").fill(key);
  await page.getByTestId("login-submit").click();
}

test("sign-in, create payment, search, and reject invalid amount", async ({ page, request }) => {
  const customer = await request.post("/api/customers", {
    headers: { "X-API-Key": API_KEY, "Content-Type": "application/json" },
    data: { customer_ref: `CUST-UI-${Date.now()}`, name: "UI Test Customer" },
  });
  expect(customer.ok()).toBeTruthy();
  const customerId = (await customer.json()).id;
  const ref = `TXN-UI-${Date.now()}`;

  await signIn(page);
  await expect(page.getByTestId("auth-status")).toHaveText("Signed in");

  await page.getByTestId("payment-customer-id").fill(String(customerId));
  await page.getByTestId("payment-amount").fill("42.50");
  await page.getByTestId("payment-ref").fill(ref);
  await page.getByTestId("payment-submit").click();
  await expect(page.getByTestId("payment-result")).toContainText("Payment accepted");
  await expect(page.getByTestId("payment-result")).toContainText(ref);
  await expect(page.getByTestId("payment-result")).toContainText("SUCCESS");

  await page.getByTestId("search-input").fill(ref);
  await page.getByTestId("search-submit").click();
  await expect(page.getByTestId("search-results")).toContainText(ref);
  await expect(page.getByTestId("search-results")).toContainText("SUCCESS");

  await page.getByTestId("payment-customer-id").fill(String(customerId));
  await page.getByTestId("payment-amount").fill("13.13");
  await page.getByTestId("payment-ref").fill(`${ref}-FAIL`);
  await page.getByTestId("payment-submit").click();
  await expect(page.getByTestId("error-banner")).toContainText("FAILED");
  await expect(page.getByTestId("payment-result")).toContainText("AMOUNT_REJECTED");
});

test("invalid API key is rejected", async ({ page }) => {
  await signIn(page, "not-a-valid-key");
  await expect(page.getByTestId("error-banner")).toContainText("Invalid API key");
  await expect(page.getByTestId("auth-status")).toHaveText("Signed out");
});
