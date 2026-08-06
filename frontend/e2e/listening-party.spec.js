import { expect, test } from "@playwright/test";
import {
  DEMO_PASSWORD,
  createBetaUsers,
  ensureBetaFixtures,
  loginAccount,
  registerAccount,
  startListeningPartyViaApi,
  uploadTrackViaApi,
} from "./helpers/beta.js";

test.describe.configure({ mode: "serial" });

const users = createBetaUsers(`party_${Date.now()}`);
const partyTitle = `First listen ${Date.now()}`;

test.beforeAll(() => {
  ensureBetaFixtures();
});

test.describe("Listening parties", () => {
  test("artist registers, uploads a track and starts a party from the studio", async ({ page }) => {
    const { audioPath } = ensureBetaFixtures();

    await registerAccount(page, { username: users.artistUser, userType: "artist" });
    await uploadTrackViaApi(page, {
      title: users.trackTitle,
      audioPath,
      username: users.artistUser,
    });

    await page.goto(`/?artist=${users.artistUser}`);
    await page.getByLabel("Artist sections").getByRole("button", { name: "Live" }).click();
    await page.getByRole("button", { name: "+ Start party" }).click();

    await page.getByLabel("Title").fill(partyTitle);
    await page.getByLabel("Featured track").selectOption({ label: users.trackTitle });
    await page.getByRole("button", { name: "Go live" }).click();

    await expect(page.getByText("Listening party started")).toBeVisible();
    await expect(page.getByRole("button", { name: "Open party room" })).toBeVisible();
  });

  test("fan joins the party, hears the unlocked track and chats", async ({ page }) => {
    await registerAccount(page, { username: users.fanUser, userType: "fan" });
    await startListeningPartyViaApi(page, {
      artistUsername: users.artistUser,
      title: partyTitle,
      trackTitle: users.trackTitle,
    });

    await loginAccount(page, users.fanUser, DEMO_PASSWORD, { force: true });
    await page.goto("/?page=live");

    await expect(page.getByRole("heading", { name: "Listening parties" })).toBeVisible();
    await page.getByRole("button", { name: "Join party" }).first().click();

    await expect(page.getByRole("heading", { name: partyTitle })).toBeVisible();
    await expect(page.getByText("Full track unlocked for this party")).toBeVisible();

    const chatInput = page.getByLabel("Chat message");
    await chatInput.fill("This track is great");
    await page.getByRole("button", { name: "Send" }).click();

    await expect(page.getByText("This track is great")).toBeVisible();
  });

  test("guest is asked to create a free account before listening along", async ({ page }) => {
    await page.context().clearCookies();
    await page.goto("/?page=live");

    await expect(page.getByRole("heading", { name: "Listening parties" })).toBeVisible();
    await page.getByRole("button", { name: "Join party" }).first().click();

    await expect(page.getByRole("heading", { name: "Listen along with a free account" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Create free account" })).toBeVisible();
  });
});
