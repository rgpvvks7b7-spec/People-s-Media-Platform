import { test, expect } from "@playwright/test";
import { registerViaApi } from "./helpers/beta.js";

test.describe("Artist onboarding checklist", () => {
  test("new artist sees launch checklist on home dashboard", async ({ page }) => {
    const stamp = Date.now();
    const username = `e2e_artist_${stamp}`;
    const stageName = `E2E Artist ${stamp}`;

    await page.goto("/");
    await registerViaApi(page, {
      username,
      userType: "artist",
      extra: {
        displayName: stageName,
        email: `${username}@example.com`,
        stageName,
        genre: "indie pop",
        city: "Melbourne",
      },
    });
    await page.goto("/?page=home");
    await expect(page.getByRole("heading", { name: "Launch your page" })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByLabel("Next best action")).toBeVisible();
  });
});
