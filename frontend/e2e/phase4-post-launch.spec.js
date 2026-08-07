import { expect, request as playwrightRequest, test } from "@playwright/test";
import {
  API,
  DEMO_PASSWORD,
  createBetaUsers,
  loginAccount,
  registerAccount,
  registerViaApi,
} from "./helpers/beta.js";

test.describe.configure({ mode: "serial" });

const stamp = Date.now();
const users = createBetaUsers(`p4_${stamp}`);
const hostUser = `p4_host_${stamp}`;
const roomName = `Phase4 Room ${stamp}`;

async function csrfHeaders(api) {
  await api.get(`${API}/accounts/current-user/`);
  const token = (await api.storageState()).cookies.find(cookie => cookie.name === "csrftoken")?.value;
  return token ? { "X-CSRFToken": token } : {};
}

/**
 * Creates a live venue listing via an isolated API context.
 */
async function createLiveListingViaApi({ hostUsername, name }) {
  const api = await playwrightRequest.newContext({
    baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:5173",
  });
  try {
    await api.post(`${API}/accounts/register/`, {
      headers: { "Content-Type": "application/json", ...(await csrfHeaders(api)) },
      data: {
        username: hostUsername,
        password: DEMO_PASSWORD,
        user_type: "host",
        display_name: "Phase4 Host",
        email: `${hostUsername}@example.com`,
        terms_accepted: true,
        discovery_location: "Melbourne",
      },
    });
    await api.post(`${API}/accounts/login/`, {
      headers: { "Content-Type": "application/json", ...(await csrfHeaders(api)) },
      data: { username: hostUsername, password: DEMO_PASSWORD },
    });
    const profileResponse = await api.post(`${API}/spaces/host-profile/`, {
      headers: { "Content-Type": "application/json", ...(await csrfHeaders(api)) },
      data: {
        business_name: "Phase4 Venue",
        contact_email: `${hostUsername}@example.com`,
        address: "44 Series St",
        city: "Melbourne",
      },
    });
    expect(profileResponse.ok(), await profileResponse.text()).toBeTruthy();

    const response = await api.post(`${API}/spaces/listings/`, {
      headers: await csrfHeaders(api),
      multipart: {
        name,
        description: "A live room for series bookings.",
        address: "44 Series St",
        city: "Melbourne",
        capacity: "40",
        available_windows: JSON.stringify([{ day: "fri", start: "19:00", end: "23:00" }]),
        split_type: "door_percent",
        host_cut_percent: "20",
        booking_mode: "request",
        status: "live",
      },
    });
    expect(response.ok(), await response.text()).toBeTruthy();
    return (await response.json()).listing;
  } finally {
    await api.dispose();
  }
}

test.describe("Phase 4 post-launch bets", () => {
  test("artist home always shows the engagement challenge board", async ({ page }) => {
    await page.goto("/");
    await registerViaApi(page, {
      username: users.artistUser,
      userType: "artist",
      extra: {
        displayName: users.artistStage,
        email: `${users.artistUser}@example.com`,
        stageName: users.artistStage,
        genre: "indie",
        city: "Melbourne",
      },
    });
    await page.goto("/?page=home");
    await expect(page.getByRole("heading", { name: "Launch your page" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Engagement board" })).toBeVisible();
    await expect(page.getByLabel("Engagement board")).toBeVisible();
  });

  test("fan my tickets has Upcoming and Collection tabs", async ({ page }) => {
    await registerAccount(page, { username: users.fanUser, userType: "fan" });
    await loginAccount(page, users.fanUser, DEMO_PASSWORD, { force: true });
    await page.goto("/?page=profile&tab=settings&section=tickets");
    await expect(page.getByText("My tickets", { exact: true }).first()).toBeVisible();
    await expect(page.getByRole("tab", { name: "Upcoming" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "Collection" })).toBeVisible();
    await page.getByRole("tab", { name: "Collection" }).click();
    await expect(page.getByText("No stubs yet")).toBeVisible();
  });

  test("artist booking form exposes series mode", async ({ page }) => {
    const listing = await createLiveListingViaApi({ hostUsername: hostUser, name: roomName });
    await loginAccount(page, users.artistUser, DEMO_PASSWORD, { force: true });
    await page.goto("/?page=spaces");
    await expect(page.getByRole("heading", { name: roomName }).first()).toBeVisible({ timeout: 15_000 });
    await page.getByRole("button", { name: "Request booking" }).first().click();
    await expect(page.getByText("Request a show")).toBeVisible();
    const seriesToggle = page.getByLabel("Book a series (up to 12 dates)");
    await expect(seriesToggle).toBeVisible();
    await seriesToggle.check();
    await expect(seriesToggle).toBeChecked();
    expect(listing.id).toBeTruthy();
  });
});
