import { expect, test } from "@playwright/test";

const API = process.env.PLAYWRIGHT_API_URL || "http://localhost:8000/api";

test.describe("IndieFund beta smoke", () => {
  test("home loads for anonymous visitors", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("INDIE").first()).toBeVisible();
  });

  test("public artist page opens without login", async ({ page }) => {
    await page.goto("/?artist=marlo_saints");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible({ timeout: 15_000 });
    await expect(page).toHaveURL(/artist=marlo_saints/);
  });

  test("fan can register and reach profile", async ({ page }) => {
    const username = `e2e_fan_${Date.now()}`;
    await page.goto("/?page=profile");
    await page.getByRole("button", { name: "Register" }).click();
    await page.getByLabel("Username").fill(username);
    await page.getByLabel("Password").fill("demo12345");
    await page.getByLabel("Display name").fill("E2E Fan");
    await page.getByLabel("Email address").fill(`${username}@example.com`);
    await page.getByLabel("Favorite genres").fill("indie pop");
    await page.getByLabel("City or region").fill("Melbourne");
    await page.getByRole("checkbox", { name: /Terms of Service and Privacy Policy/i }).check();
    await page.getByRole("button", { name: "Create Account" }).click();
    await expect(page.getByLabel("Primary navigation").getByText("E2E Fan")).toBeVisible({ timeout: 15_000 });
  });

  test("privacy policy page loads for guests", async ({ page }) => {
    await page.goto("/?page=privacy");
    await expect(page.getByRole("heading", { level: 1, name: "Privacy Policy" })).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Legal" })).toBeVisible();
  });

  test("cookie policy page loads for guests", async ({ page }) => {
    await page.goto("/?page=cookies");
    await expect(page.getByRole("heading", { level: 1, name: "Cookie Policy" })).toBeVisible();
    await expect(page.getByRole("heading", { name: /no advertising cookies/i })).toBeVisible();
  });

  test("public artist meta endpoint responds", async ({ request }) => {
    const response = await request.get(`${API}/artists/public/marlo_saints/`);
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.stage_name).toBeTruthy();
    expect(data.page_url).toContain("artist=marlo_saints");
  });
});
