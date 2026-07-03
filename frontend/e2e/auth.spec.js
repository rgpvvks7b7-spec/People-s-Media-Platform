import { expect, test } from "@playwright/test";
import { DEMO_PASSWORD } from "./helpers/beta.js";

test("guest can open FAQ from landing", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "How it works" }).click();
  await expect(page.getByRole("heading", { name: "Frequently asked questions" })).toBeVisible();
  await expect(page.getByText("support@indiefund.app")).toBeVisible();
});

test("guest global search finds seeded artist", async ({ page }) => {
  await page.goto("/?page=listen");
  await page.getByRole("textbox", { name: "Search artists, tracks, and posts" }).fill("luna");
  await expect(page.getByRole("listbox", { name: "Search results" })).toBeVisible({ timeout: 15000 });
  await expect(page.getByRole("button", { name: /Artist: Luna Lane/i })).toBeVisible();
});

test("registration requires terms acceptance", async ({ page }) => {
  const user = `terms_fan_${Date.now()}`;
  await page.goto("/?page=profile");
  await page.getByRole("button", { name: "Register" }).click();
  await page.getByLabel("Username").fill(user);
  await page.getByLabel("Password").fill(DEMO_PASSWORD);
  await page.getByLabel("Display name").fill("Terms Fan");
  await page.getByLabel("Email address").fill(`${user}@example.com`);
  await page.getByLabel("Favorite genres").fill("indie pop");
  await page.getByLabel("City or region").fill("Melbourne");
  await page.getByRole("button", { name: "Create Account" }).click();
  await expect(page.getByText(/accept the Terms/i)).toBeVisible();
});
