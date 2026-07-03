import { chromium } from "@playwright/test";

const FRONTEND = (process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:5173").replace(/\/$/, "");
const API = `${FRONTEND}/api`;
const PASSWORD = "demo12345";

const SESSIONS = [
  { label: "Fan", username: "demo_fan", path: "/?page=discover" },
  { label: "Artist", username: "luna_lane", path: "/?page=home" },
  { label: "Host", username: "team_host", path: "/?page=spaces" },
];

async function loginViaApi(page, username) {
  await page.goto(`${FRONTEND}/?page=profile`);
  await page.request.get(`${API}/accounts/current-user/`);
  const csrf = (await page.context().cookies()).find(c => c.name === "csrftoken")?.value;
  const res = await page.request.post(`${API}/accounts/login/`, {
    headers: {
      "Content-Type": "application/json",
      ...(csrf ? { "X-CSRFToken": csrf } : {}),
    },
    data: { username, password: PASSWORD },
  });
  if (!res.ok()) {
    throw new Error(`Login failed for ${username}: ${await res.text()}`);
  }
}

async function main() {
  for (const session of SESSIONS) {
    const browser = await chromium.launch({ headless: false });
    const page = await browser.newPage();
    await loginViaApi(page, session.username);
    await page.goto(`${FRONTEND}${session.path}`);
    await page.bringToFront();
    console.log(`Opened ${session.label} (${session.username}) → ${session.path}`);
  }
  console.log("Three browser windows are open. Close them or press Ctrl+C here to exit.");
  await new Promise(() => {});
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
