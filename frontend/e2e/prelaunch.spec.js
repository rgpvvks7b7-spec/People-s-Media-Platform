import { test, expect } from "@playwright/test";

const API = process.env.PLAYWRIGHT_API_URL || "http://127.0.0.1:8000/api";

test.describe("Prelaunch platform mode", () => {
  test("health reports prelaunch", async ({ request }) => {
    const response = await request.get(`${API}/health/`);
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.platform_mode).toBe("prelaunch");
    expect(data.fan_registration_open).toBe(false);
  });

  test("guest listen route shows coming soon gate", async ({ page }) => {
    await page.goto("/?page=listen");
    await expect(page.getByRole("heading", { name: "Fan features open at launch" })).toBeVisible();
  });

  test("early access landing promotes creator signup", async ({ page }) => {
    await page.goto("/?page=early-access");
    await expect(page.getByRole("heading", { name: /get listed before fans arrive/i })).toBeVisible();
    await expect(page.getByRole("button", { name: "Artist early signup" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Join fan waitlist" }).first()).toBeVisible();
  });

  test("guest home promotes creator early signup", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /get listed before fans arrive/i })).toBeVisible();
    await expect(page.getByRole("button", { name: "Artist early signup" })).toBeVisible();
  });

  test("registration hides fan account type", async ({ page }) => {
    await page.goto("/?page=profile");
    await page.getByRole("button", { name: "Register" }).click();
    await expect(page.getByLabel("Account type")).toBeVisible();
    await expect(page.getByLabel("Account type").locator("option")).toHaveCount(2);
  });

  test("fan waitlist form submits in prelaunch", async ({ page }) => {
    const email = `waitlist_${Date.now()}@example.com`;
    await page.goto("/?page=profile");
    await page.getByRole("button", { name: "Fan waitlist" }).click();
    await page.getByLabel("Email address").fill(email);
    await page.getByLabel("City or region").fill("Melbourne");
    await page.getByLabel(/privacy policy/i).check();
    await page.getByRole("button", { name: "Join waitlist" }).click();
    await expect(page.getByText(/waitlist/i).first()).toBeVisible();
  });
});
