import { expect, request as playwrightRequest, test } from "@playwright/test";
import {
  API,
  DEMO_PASSWORD,
  createBetaUsers,
  loginAccount,
  registerAccount,
  startListeningPartyViaApi,
} from "./helpers/beta.js";

test.describe.configure({ mode: "serial" });

const stamp = Date.now();
const users = createBetaUsers(`p5_${stamp}`);

/**
 * Stops a listening party with an isolated API context so the browser fan
 * session is never overwritten by the host login.
 */
async function stopListeningPartyViaApi({ artistUsername, sessionId }) {
  const api = await playwrightRequest.newContext({
    baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:5173",
  });
  try {
    await api.post(`${API}/accounts/login/`, {
      data: { username: artistUsername, password: DEMO_PASSWORD },
    });
    const response = await api.post(`${API}/live/${sessionId}/stop/`);
    expect(response.ok(), await response.text()).toBeTruthy();
  } finally {
    await api.dispose();
  }
}

test.describe("Phase 5 engagement loop", () => {
  test("artist home shows invite funnel analytics", async ({ page }) => {
    await registerAccount(page, {
      username: users.artistUser,
      userType: "artist",
      stageName: users.artistStage,
    });
    await page.goto("/?page=home");

    await expect(page.getByRole("heading", { name: /Welcome back|Business health/ })).toBeVisible();
    await expect(page.getByText("Invite funnel")).toBeVisible();
  });

  test("free arts artist sees commission inbox upgrade teaser", async ({ page, request }) => {
    const artsUser = `p5_arts_${stamp}`;
    await request.post(`${API}/accounts/register/`, {
      data: {
        username: artsUser,
        password: DEMO_PASSWORD,
        user_type: "artist",
        display_name: "Phase Five Arts",
        email: `${artsUser}@example.com`,
        terms_accepted: true,
        stage_name: "Phase Five Arts",
        genre: "visual",
        city: "Melbourne",
        professions: ["visual_art"],
      },
    });
    await loginAccount(page, artsUser, DEMO_PASSWORD, { force: true });
    await page.goto(`/?artist=${artsUser}`);

    await expect(page.getByRole("heading", { name: /inbox/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Artist Pro unlocks your commission inbox" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Upgrade to Artist Pro" })).toBeVisible();
  });

  test("ended listening party offers tip CTA for fans", async ({ page, request }) => {
    const partyArtist = `p5_party_artist_${stamp}`;
    const partyFan = `p5_party_fan_${stamp}`;
    const partyTitle = `Phase5 Party ${stamp}`;

    await request.post(`${API}/accounts/register/`, {
      data: {
        username: partyArtist,
        password: DEMO_PASSWORD,
        user_type: "artist",
        display_name: "Phase Five Party",
        email: `${partyArtist}@example.com`,
        terms_accepted: true,
        stage_name: "Phase Five Party",
        genre: "indie",
        city: "Melbourne",
        professions: ["music"],
      },
    });

    const session = await startListeningPartyViaApi({
      artistUsername: partyArtist,
      title: partyTitle,
    });

    await registerAccount(page, { username: partyFan, userType: "fan" });
    await page.goto("/?page=live");
    await expect(page.getByRole("heading", { name: "Listening parties" })).toBeVisible();
    await page.getByRole("button", { name: "Join party" }).first().click();
    await expect(page.getByRole("heading", { name: partyTitle })).toBeVisible();

    await stopListeningPartyViaApi({ artistUsername: partyArtist, sessionId: session.id });
    await expect(page.getByRole("heading", { name: "This party has ended." })).toBeVisible();
    await page.getByRole("button", { name: "Tip Phase Five Party" }).click();
    await expect(page.getByRole("heading", { name: "Tip Phase Five Party" })).toBeVisible();
    await expect(page.getByRole("button", { name: /Send \$/ })).toBeVisible();
  });
});
