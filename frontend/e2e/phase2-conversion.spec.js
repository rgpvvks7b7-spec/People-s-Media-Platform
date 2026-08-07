import { expect, test } from "@playwright/test";
import {
  API,
  DEMO_PASSWORD,
  createBetaUsers,
  loginAccount,
  registerViaApi,
} from "./helpers/beta.js";

test.describe.configure({ mode: "serial" });

const stamp = Date.now();
const users = createBetaUsers(`p2_${stamp}`);

test.describe("Phase 2 conversion funnel", () => {
  test("public pricing page shows fee calculator keep total", async ({ page }) => {
    await page.goto("/?page=pricing");
    await expect(page.getByRole("heading", { name: "Pricing & fee calculator" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "Free" })).toBeVisible();
    await expect(page.getByText(/You keep \$/i)).toBeVisible();
    await page.getByRole("tab", { name: "Studio" }).click();
    await expect(page.getByRole("tab", { name: "Studio" })).toHaveAttribute("aria-selected", "true");
    await expect(page.getByText(/You keep \$/i)).toBeVisible();
  });

  test("artist upload form offers 10/30/60 preview presets", async ({ page }) => {
    await page.goto("/");
    await registerViaApi(page, {
      username: users.artistUser,
      userType: "artist",
      extra: {
        displayName: users.artistStage,
        email: `${users.artistUser}@example.com`,
        stageName: users.artistStage,
        genre: "indie",
        city: "Melbourne",
      },
    });
    await page.goto("/?page=home");
    await page.getByRole("button", { name: "Upload track" }).click();
    await expect(page.getByRole("heading", { name: "Upload Track" })).toBeVisible();
    await expect(page.getByLabel("Preview length")).toBeVisible();
    await expect(page.getByLabel("Preview length").getByRole("option")).toHaveCount(3);
  });

  test("fan library shows support slot count", async ({ page }) => {
    await registerViaApi(page, {
      username: users.fanUser,
      userType: "fan",
      extra: {
        displayName: "Phase2 Fan",
        email: `${users.fanUser}@example.com`,
      },
    });
    await loginAccount(page, users.fanUser, DEMO_PASSWORD, { force: true });
    await page.goto("/?page=profile&tab=settings&section=library");
    await expect(page.getByText(/of 50 slots/i)).toBeVisible();
  });

  test("fee schedule API returns calculator payload", async ({ request }) => {
    const response = await request.get(`${API}/accounts/fee-schedule/?plan=pro&support_gmv=200&tips_gmv=50&marketplace_gmv=100`);
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.schedule.plan).toBe("pro");
    expect(data.calculator.you_keep_total).toBeTruthy();
    expect(data.plans).toContain("studio");
  });
});
