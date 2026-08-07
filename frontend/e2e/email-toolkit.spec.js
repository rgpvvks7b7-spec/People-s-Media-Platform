import { expect, request as playwrightRequest, test } from "@playwright/test";
import {
  API,
  DEMO_PASSWORD,
  createBetaUsers,
  loginAccount,
  registerAccount,
} from "./helpers/beta.js";

test.describe.configure({ mode: "serial" });

const stamp = Date.now();
const users = createBetaUsers(`mail_${stamp}`);

async function csrfHeaders(api) {
  await api.get(`${API}/accounts/current-user/`);
  const token = (await api.storageState()).cookies.find(cookie => cookie.name === "csrftoken")?.value;
  return token ? { "X-CSRFToken": token } : {};
}

/**
 * Seeds N opted-in mailing contacts for an artist using isolated API contexts.
 */
async function seedMailingContacts({ artistUsername, count }) {
  const artistApi = await playwrightRequest.newContext({
    baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:5173",
  });
  try {
    await artistApi.post(`${API}/accounts/login/`, {
      headers: { "Content-Type": "application/json", ...(await csrfHeaders(artistApi)) },
      data: { username: artistUsername, password: DEMO_PASSWORD },
    });
    const me = await artistApi.get(`${API}/accounts/current-user/`);
    expect(me.ok(), await me.text()).toBeTruthy();
    const meData = await me.json();
    const artistId = meData.user?.id || meData.id;
    expect(artistId).toBeTruthy();

    for (let index = 0; index < count; index += 1) {
      const fan = `mail_seed_${stamp}_${index}`;
      const fanApi = await playwrightRequest.newContext({
        baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:5173",
      });
      try {
        await fanApi.post(`${API}/accounts/register/`, {
          headers: { "Content-Type": "application/json", ...(await csrfHeaders(fanApi)) },
          data: {
            username: fan,
            password: DEMO_PASSWORD,
            user_type: "fan",
            display_name: fan,
            email: `${fan}@example.com`,
            terms_accepted: true,
            discovery_location: "Melbourne",
          },
        });
        await fanApi.post(`${API}/accounts/login/`, {
          headers: { "Content-Type": "application/json", ...(await csrfHeaders(fanApi)) },
          data: { username: fan, password: DEMO_PASSWORD },
        });
        const share = await fanApi.post(`${API}/artists/fan-email-sharing/`, {
          headers: { "Content-Type": "application/json", ...(await csrfHeaders(fanApi)) },
          data: { artist_id: artistId, email_shared: true },
        });
        expect(share.ok(), await share.text()).toBeTruthy();
      } finally {
        await fanApi.dispose();
      }
    }
  } finally {
    await artistApi.dispose();
  }
}

test.describe("Artist email toolkit", () => {
  test("artist opens mailing list studio with templates and local draw", async ({ page }) => {
    await registerAccount(page, {
      username: users.artistUser,
      userType: "artist",
      extra: { stageName: users.artistStage },
    });
    await page.goto("/?page=mailing-list");

    await expect(page.getByRole("heading", { name: "Mailing list" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Email template studio" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Local draw playbook" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "No emails shared yet" })).toBeVisible();

    await page.getByRole("tab", { name: "Upcoming local show" }).click();
    await expect(page.getByLabel("Subject")).toHaveValue(/live/i);
    await page.getByRole("button", { name: "Copy draft" }).click();
    await expect(page.getByText(/copied|Select the draft/i)).toBeVisible();
  });

  test("free artist with 10 contacts sees export nudge", async ({ page, request }) => {
    const artist = `mail_nudge_${stamp}`;
    await request.post(`${API}/accounts/register/`, {
      data: {
        username: artist,
        password: DEMO_PASSWORD,
        user_type: "artist",
        display_name: "Nudge Artist",
        email: `${artist}@example.com`,
        terms_accepted: true,
        stage_name: "Nudge Artist",
        genre: "indie",
        city: "Melbourne",
        professions: ["music"],
      },
    });
    await seedMailingContacts({ artistUsername: artist, count: 10 });
    await loginAccount(page, artist, DEMO_PASSWORD, { force: true });
    await page.goto("/?page=mailing-list");
    await expect(page.getByRole("heading", { name: "You have 10 opted-in contacts" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Unlock CSV export" })).toBeVisible();
  });

  test("fans CRM mailing segment bridges to draft", async ({ page }) => {
    await loginAccount(page, users.artistUser, DEMO_PASSWORD, { force: true });
    await page.goto("/?page=fans");
    await page.getByRole("tab", { name: /Mailing list/ }).click();
    await expect(page.getByRole("button", { name: "Copy email draft" })).toBeVisible();
    await page.getByRole("button", { name: "Copy email draft" }).click();
    await expect(page.getByRole("heading", { name: "Email template studio" })).toBeVisible();
  });
});
