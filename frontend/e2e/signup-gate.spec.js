import { expect, test } from "@playwright/test";
import { DEMO_PASSWORD, createBetaUsers, registerViaApi } from "./helpers/beta.js";

test.describe.configure({ mode: "serial" });

const stamp = Date.now();
const users = createBetaUsers(`gate_${stamp}`);
const stageName = `Gate Artist ${stamp}`;

test.describe("Guest signup gates", () => {
  test("guest hitting follow on an artist page signs up and resumes as a follower", async ({ page }) => {
    await registerViaApi(page, {
      username: users.artistUser,
      userType: "artist",
      extra: { stageName },
    });
    await page.context().clearCookies();

    await page.goto(`/?artist=${users.artistUser}`);
    await page.getByRole("button", { name: "Log in or sign up" }).click();

    const gate = page.getByRole("dialog");
    await expect(gate.getByRole("heading", { name: `Follow ${stageName} for free` })).toBeVisible();
    await gate.getByRole("button", { name: "Create free fan account" }).click();

    await expect(page.getByRole("heading", { name: "Create your account" })).toBeVisible();
    await expect(page.getByLabel("Account type")).toHaveValue("fan");

    await page.getByLabel("Username").fill(users.fanUser);
    await page.getByLabel("Password").fill(DEMO_PASSWORD);
    await page.getByLabel("Display name").fill("Gate Fan");
    await page.getByLabel("Email address").fill(`${users.fanUser}@example.com`);
    await page.getByLabel("Favorite genres", { exact: false }).fill("indie pop");
    await page.getByLabel("City or region").fill("Melbourne");
    await page.getByLabel(/I agree to the Terms of Service/).check();
    await page.getByRole("button", { name: "Create Account" }).click();

    await expect(page.getByText(`You're following ${stageName}`)).toBeVisible();
    await expect(page).toHaveURL(new RegExp(`artist=${users.artistUser}`));
  });

  test("guest on My Scene sees the tickets gate and can dismiss it", async ({ page }) => {
    await page.goto("/?page=my-scene");
    await page.getByRole("button", { name: "Sign up or log in" }).click();

    const gate = page.getByRole("dialog");
    await expect(gate.getByRole("heading", { name: "See shows near you" })).toBeVisible();
    await expect(gate.getByRole("button", { name: "Create free fan account" })).toBeVisible();

    await gate.getByRole("button", { name: "Not now" }).click();
    await expect(gate).toBeHidden();
  });
});
