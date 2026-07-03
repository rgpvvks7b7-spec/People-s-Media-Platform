import { test, expect } from "@playwright/test";
import { loginAccount, DEMO_PASSWORD } from "./helpers/beta.js";

test.describe("Artist studio merch nav", () => {
  test.beforeEach(async ({ page }) => {
    await loginAccount(page, "luna_lane", DEMO_PASSWORD, { force: true });
    await page.goto("/?artist=luna_lane&profession=music");
    const cookieOk = page.getByRole("button", { name: "OK" });
    if (await cookieOk.isVisible().catch(() => false)) {
      await cookieOk.click();
    }
  });

  test("sidebar Merch opens merch store with readable active label", async ({ page }) => {
    const sidebar = page.getByRole("complementary", { name: "Primary navigation" });
    const merchButton = sidebar.getByRole("button", { name: /Merch/i });
    await merchButton.click();

    await expect(page).toHaveURL(/tab=merch/);
    await expect(page.getByRole("heading", { name: "Merch Store" })).toBeVisible();
    await expect(merchButton).toHaveAttribute("aria-current", "page");

    const labelColor = await merchButton.locator(".app-nav-copy span").evaluate((el) => {
      const style = window.getComputedStyle(el);
      return { color: style.color, background: style.backgroundColor };
    });
    expect(labelColor.color).not.toBe("rgb(0, 0, 0)");

    const iconColor = await merchButton.locator(".app-nav-icon").evaluate((el) => window.getComputedStyle(el).color);
    expect(iconColor).toBe("rgb(255, 255, 255)");
  });
});
