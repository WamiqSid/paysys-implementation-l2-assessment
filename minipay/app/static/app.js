const state = { apiKey: sessionStorage.getItem("minipayApiKey") || "" };

const errorBanner = document.getElementById("error-banner");
const authStatus = document.getElementById("auth-status");
const workArea = document.getElementById("work-area");
const loginCard = document.getElementById("login-card");

function showError(message) {
  errorBanner.textContent = message;
  errorBanner.classList.toggle("hidden", !message);
}

function setSignedIn(on) {
  authStatus.textContent = on ? "Signed in" : "Signed out";
  authStatus.className = on ? "pill pill-ok" : "pill pill-warn";
  authStatus.dataset.signedIn = on ? "true" : "false";
  workArea.classList.toggle("hidden", !on);
  loginCard.classList.toggle("hidden", on);
}

async function api(path, options = {}) {
  showError("");
  const headers = Object.assign(
    { "Content-Type": "application/json", "X-API-Key": state.apiKey },
    options.headers || {}
  );
  const response = await fetch(path, { ...options, headers });
  const text = await response.text();
  let body = null;
  try { body = text ? JSON.parse(text) : null; } catch { body = { raw: text }; }
  if (!response.ok) {
    const detail = body && body.detail ? body.detail : `HTTP ${response.status}`;
    const error = new Error(detail);
    error.status = response.status;
    error.body = body;
    throw error;
  }
  return body;
}

function renderPayments(target, items, extra) {
  if (!items || items.length === 0) {
    target.innerHTML = `<p class="bad">No transactions found.</p>`;
    return;
  }
  const note = extra ? `<p>${extra}</p>` : "";
  target.innerHTML = note + items.map((tx) => `
    <div class="tx">
      <div><strong data-ref="${tx.transaction_ref}">${tx.transaction_ref}</strong> · id ${tx.id}</div>
      <div>customer ${tx.customer_id} · amount ${tx.amount}</div>
      <div class="${tx.status === "SUCCESS" ? "ok" : "bad"}">status ${tx.status}${tx.failure_code ? " (" + tx.failure_code + ")" : ""}</div>
    </div>
  `).join("");
}

document.getElementById("login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  state.apiKey = document.getElementById("login-key").value.trim();
  try {
    await api("/api/ops/health");
    sessionStorage.setItem("minipayApiKey", state.apiKey);
    setSignedIn(true);
  } catch (err) {
    sessionStorage.removeItem("minipayApiKey");
    setSignedIn(false);
    showError(err.message || "Sign-in failed");
  }
});

document.getElementById("search-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const q = document.getElementById("search-input").value.trim();
  const target = document.getElementById("search-results");
  try {
    const result = await api(`/api/search?q=${encodeURIComponent(q)}`);
    const extra = result.duplicate_ref
      ? `Duplicate transaction_ref detected (${result.count} rows).`
      : `Found ${result.count} row(s).`;
    renderPayments(target, result.items, extra);
    if (result.count === 0) showError("Transaction not found");
  } catch (err) {
    target.innerHTML = "";
    showError(err.message || "Search failed");
  }
});

document.getElementById("payment-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const target = document.getElementById("payment-result");
  const payload = {
    customer_id: Number(document.getElementById("payment-customer-id").value),
    amount: document.getElementById("payment-amount").value,
  };
  const ref = document.getElementById("payment-ref").value.trim();
  if (ref) payload.transaction_ref = ref;
  try {
    const tx = await api("/api/payments", { method: "POST", body: JSON.stringify(payload) });
    const extra = tx.status === "SUCCESS" ? "Payment accepted." : "Payment was not successful.";
    renderPayments(target, [tx], extra);
    if (tx.status !== "SUCCESS") showError(`Payment ${tx.status}${tx.failure_code ? ": " + tx.failure_code : ""}`);
  } catch (err) {
    target.innerHTML = "";
    showError(err.message || "Payment failed");
  }
});

if (state.apiKey) {
  api("/api/ops/health").then(() => {
    document.getElementById("login-key").value = state.apiKey;
    setSignedIn(true);
  }).catch(() => setSignedIn(false));
} else {
  setSignedIn(false);
}
