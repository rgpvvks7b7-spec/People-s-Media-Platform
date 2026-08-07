import { expect, test } from "@playwright/test";
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
const users = createBetaUsers(`p3_${stamp}`);
const hostUser = `p3_host_${stamp}`;
const roomName = `Phase3 Room ${stamp}`;

async function createLiveListing(page, { hostUsername, name }) {
  await loginAccount(page, hostUsername, DEMO_PASSWORD, { force: true });
  await page.request.post(`${API}/spaces/host-profile/`, {
    data: {
      business_name: "Phase3 Venue",
      contact_email: `${hostUsername}@example.com`,
      address: "12 Test Lane",
      city: "Melbourne",
    },
  });
  const response = await page.request.post(`${API}/spaces/listings/`, {
    multipart: {
      name,
      description: "A live room for independent artists.",
      address: "12 Test Lane",
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
}

test.describe("Phase 3 growth surfaces", () => {
  test("artist embed widget is frameable HTML", async ({ request }) => {
    await request.post(`${API}/accounts/register/`, {
      data: {
        username: users.artistUser,
        password: DEMO_PASSWORD,
        user_type: "artist",
        display_name: "Phase Three Artist",
        email: `${users.artistUser}@example.com`,
        terms_accepted: true,
        stage_name: "Phase Three Artist",
        genre: "indie",
        city: "Melbourne",
        professions: ["music"],
      },
    });

    const response = await request.get(`${API}/artists/public/${users.artistUser}/embed/`);
    expect(response.ok()).toBeTruthy();
    expect(response.headers()["content-type"]).toContain("text/html");
    expect(response.headers()["content-security-policy"]).toBe("frame-ancestors *");
    expect(response.headers()["x-frame-options"]).toBeFalsy();
    const body = await response.text();
    expect(body).toContain("Phase Three Artist");
    expect(body).toContain("Support on IndieFund");
  });

  test("fan can open a public venue page and follow it", async ({ page }) => {
    await registerViaApi(page, { username: hostUser, userType: "host" });
    const listing = await createLiveListing(page, { hostUsername: hostUser, name: roomName });

    await registerAccount(page, { username: users.fanUser, userType: "fan" });
    await page.goto(`/?page=spaces&listing=${listing.id}`);

    await expect(page.getByRole("heading", { name: roomName })).toBeVisible();
    await page.getByRole("button", { name: "Follow venue" }).click();
    await expect(page.getByRole("button", { name: "Following venue" })).toBeVisible();
  });
});
