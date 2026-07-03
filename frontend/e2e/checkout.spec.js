import { expect, test } from "@playwright/test";
import {
  DEMO_PASSWORD,
  loginAccount,
  registerViaApi,
  seedStoreCart,
  sendTipViaApi,
  subscribeArtistViaApi,
} from "./helpers/beta.js";

const STORE_ARTIST = "luna_lane";

test.describe.configure({ mode: "serial" });

test.describe("Checkout flows (beta payment mode)", () => {
  const fan = `checkout_fan_${Date.now()}`;

  async function openArtist(page, username) {
    await page.goto(`/?artist=${username}`);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible({ timeout: 15000 });
  }

  test("fan subscribes to an artist", async ({ page }) => {
    await registerViaApi(page, {
      username: fan,
      userType: "fan",
      extra: {
        displayName: "Checkout Fan",
        email: `${fan}@example.com`,
        favoriteGenres: "indie pop",
        discoveryLocation: "Melbourne",
      },
    });
    await loginAccount(page, fan, DEMO_PASSWORD, { force: true });
    await subscribeArtistViaApi(page, { fanUsername: fan, artistUsername: STORE_ARTIST });
    await expect(page.getByRole("button", { name: "Account menu" })).toBeVisible({ timeout: 15000 });
  });

  test("fan sends a one-time tip", async ({ page }) => {
    await sendTipViaApi(page, { fanUsername: fan, artistUsername: STORE_ARTIST });
    await page.goto("/?page=home");
    await expect(page.getByRole("button", { name: "Account menu" })).toBeVisible({ timeout: 15000 });
    await openArtist(page, STORE_ARTIST);
    await expect(page.getByRole("heading", { name: "Recent Tips" })).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(fan).first()).toBeVisible({ timeout: 15000 });
  });

  test("fan buys a show ticket", async ({ page }) => {
    await loginAccount(page, fan, DEMO_PASSWORD);
    await page.goto("/?page=my-scene");
    await page.getByRole("button", { name: /All nearby/ }).click();

    const buyTicket = page.getByRole("button", { name: /Buy ticket/ }).first();
    await expect(buyTicket).toBeVisible({ timeout: 15000 });
    await buyTicket.click();

    await expect(page.getByText(/Ticket confirmed|Purchase confirmed|You already have a ticket/i).first()).toBeVisible({ timeout: 20000 });
  });

  test("fan checks out a store cart", async ({ page }) => {
    await loginAccount(page, fan, DEMO_PASSWORD, { force: true });
    await seedStoreCart(page);

    await page.getByRole("button", { name: "Store cart" }).click();
    await page.getByRole("button", { name: "Checkout cart" }).click();
    await expect(page.getByText(/Cart purchase|purchase recorded/i).first()).toBeVisible({ timeout: 20000 });
  });
});
