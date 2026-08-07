import { expect, test } from "@playwright/test";
import { createBetaUsers, registerAccount } from "./helpers/beta.js";

test.describe.configure({ mode: "serial" });

const users = createBetaUsers(`tiers_${Date.now()}`);

test.describe("Support tier templates", () => {
  test("artist launches the $1 + $5 starter pack in one click", async ({ page }) => {
    await registerAccount(page, { username: users.artistUser, userType: "artist" });
    await page.goto(`/?artist=${users.artistUser}`);

    await page.getByLabel("Artist sections").getByRole("button", { name: "More" }).click();
    await page.getByLabel("More").getByRole("button", { name: "Support tier editor" }).click();

    await expect(page.getByRole("heading", { name: "Support tier editor" })).toBeVisible();
    await page.getByRole("button", { name: "Launch starter pack" }).click();

    await expect(page.getByText("Starter pack live")).toBeVisible();
    await expect(page.getByRole("button", { name: "Launch starter pack" })).toHaveCount(0);
    await expect(page.getByText("$1.00/month").first()).toBeVisible();
    await expect(page.getByText("$5.00/month").first()).toBeVisible();
    await expect(page.getByText("Supporter", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Member", { exact: true }).first()).toBeVisible();
  });
});
