import fs from "fs";
import path from "path";
import { expect, test } from "@playwright/test";
import {
  API,
  DEMO_PASSWORD,
  SCREENSHOT_DIR,
  createBetaUsers,
  ensureBetaFixtures,
  loginAccount,
  openArtistPosts,
  openArtistStudio,
  registerAccount,
  snap,
  uploadTrackViaApi,
  waitForToast,
  followArtistViaApi,
  subscribeArtistViaApi,
  createPostViaApi,
} from "./helpers/beta.js";

test.describe.configure({ mode: "serial" });

const users = createBetaUsers();

const ARTIST_DASHBOARD_HEADING = /Business health|Welcome back/i;

const ALL_BETA_ACCOUNTS = [
  { username: "static_harbor", label: "Legacy artist", nav: "Dashboard", heading: ARTIST_DASHBOARD_HEADING },
  { username: "mika_north", label: "Legacy artist", nav: "Dashboard", heading: ARTIST_DASHBOARD_HEADING },
  { username: "marlo_saints", label: "Legacy artist", nav: "Dashboard", heading: ARTIST_DASHBOARD_HEADING },
  { username: "team_fan", label: "Team fan", path: "/?page=listen", heading: "Listen" },
  { username: "team_artist", label: "Team artist", nav: "Dashboard", heading: ARTIST_DASHBOARD_HEADING },
  { username: "team_host", label: "Team host", nav: "Spaces", heading: "Your rooms" },
  { username: "team_fan_sydney", label: "Team fan Sydney", path: "/?page=listen", heading: "Listen" },
  { username: "team_artist_sydney", label: "Team artist Sydney", nav: "Dashboard", heading: ARTIST_DASHBOARD_HEADING },
  { username: "team_promoter", label: "Team promoter", nav: "Promote Discovery ads", heading: "Promote your release" },
];

test.beforeAll(() => {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
  ensureBetaFixtures();
});

test.describe("Beta API health", () => {
  test("accounts endpoint responds", async ({ request }) => {
    const response = await request.get(`${API}/accounts/`);
    expect(response.ok()).toBeTruthy();
  });

  test("public artist meta responds", async ({ request }) => {
    const response = await request.get(`${API}/artists/public/marlo_saints/`);
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.stage_name).toBeTruthy();
    expect(data.page_url).toContain("artist=marlo_saints");
  });

  test("discovery artists endpoint responds", async ({ request }) => {
    const response = await request.get(`${API}/discovery/artists/`);
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(Array.isArray(data.results)).toBeTruthy();
  });
});

test.describe("Guest beta smoke", () => {
  test("home loads for anonymous visitors", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("INDIE").first()).toBeVisible();
  });

  test("public artist page opens without login", async ({ page }) => {
    await page.goto("/?artist=marlo_saints");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible({ timeout: 15000 });
    await expect(page).toHaveURL(/artist=marlo_saints/);
  });
});

test.describe("Seeded demo accounts", () => {
  test("demo fan can open listen", async ({ page }) => {
    await loginAccount(page, "demo_fan", DEMO_PASSWORD);
    await page.goto("/?page=listen");
    await expect(page.getByRole("heading", { name: "Listen" })).toBeVisible({ timeout: 15000 });
    await snap(page, "demo-fan-listen");
  });

  test("demo fan can open shows near me", async ({ page }) => {
    await loginAccount(page, "demo_fan", DEMO_PASSWORD);
    await page.goto("/?page=my-scene");
    await expect(page.getByRole("heading", { name: /Local shows near you|Shows near/i })).toBeVisible({ timeout: 15000 });
    await snap(page, "demo-fan-shows-near-me");
  });

  test("demo artist can open dashboard", async ({ page }) => {
    await loginAccount(page, "luna_lane", DEMO_PASSWORD);
    await page.getByRole("button", { name: "Dashboard" }).click();
    await expect(page.getByRole("heading", { name: ARTIST_DASHBOARD_HEADING })).toBeVisible({ timeout: 15000 });
    await snap(page, "demo-artist-dashboard");
  });
});

test.describe("All beta accounts smoke", () => {
  test("every beta team and legacy account reaches its core screen", async ({ page }) => {
    for (const account of ALL_BETA_ACCOUNTS) {
      await loginAccount(page, account.username, DEMO_PASSWORD, { force: true });
      if (account.path) {
        await page.goto(account.path);
      } else {
        await page.getByRole("button", { name: account.nav }).click();
      }
      await expect(page.getByRole("heading", { name: account.heading })).toBeVisible({ timeout: 15000 });
      await snap(page, `account-${account.username}`);
    }
  });
});

test.describe.serial("New user beta journey", () => {
  test("fan registers", async ({ page }) => {
    await registerAccount(page, {
      username: users.fanUser,
      userType: "fan",
      extra: {
        displayName: "Beta Fan",
        email: `${users.fanUser}@example.com`,
      },
    });
    await snap(page, "01-fan-register");
    await expect(page.getByLabel("Primary navigation").getByText("Beta Fan")).toBeVisible({ timeout: 15000 });
  });

  test("artist registers", async ({ page }) => {
    await registerAccount(page, {
      username: users.artistUser,
      userType: "artist",
      extra: {
        displayName: users.artistStage,
        email: `${users.artistUser}@example.com`,
        stageName: users.artistStage,
        genre: "indie pop",
        city: "Melbourne",
      },
    });
    await snap(page, "02-artist-register");
    await expect(page.getByLabel("Primary navigation").getByText(users.artistStage)).toBeVisible({ timeout: 15000 });
  });

  test("artist uploads music", async ({ page }) => {
    const { audioPath } = ensureBetaFixtures();

    await loginAccount(page, users.artistUser, DEMO_PASSWORD, { force: true });
    await uploadTrackViaApi(page, {
      title: users.trackTitle,
      audioPath,
      username: users.artistUser,
    });
    await page.goto(`/?artist=${users.artistUser}`);
    await expect(page.getByText(users.trackTitle).first()).toBeVisible({ timeout: 15000 });
    await snap(page, "03-artist-upload-music");
  });

  test("fan follows artist", async ({ page }) => {
    await followArtistViaApi(page, { fanUsername: users.fanUser, artistUsername: users.artistUser });
    await loginAccount(page, users.fanUser, DEMO_PASSWORD, { force: true });
    await page.goto(`/?artist=${users.artistUser}`);
    await page.reload();
    await snap(page, "04-fan-follow-artist");
    await expect(page.getByRole("button", { name: "Following" })).toBeVisible({ timeout: 15000 });
  });

  test("fan buys subscription", async ({ page }) => {
    await subscribeArtistViaApi(page, { fanUsername: users.fanUser, artistUsername: users.artistUser });
    await loginAccount(page, users.fanUser, DEMO_PASSWORD, { force: true });
    await page.goto(`/?artist=${users.artistUser}`);
    await page.reload();
    await snap(page, "05-fan-subscription");
    await expect(page.getByRole("button", { name: "Manage support" })).toBeVisible({ timeout: 15000 });
  });

  test("artist creates post", async ({ page }) => {
    await createPostViaApi(page, {
      artistUsername: users.artistUser,
      title: users.postTitle,
      body: "Beta test post body — Playwright automated beta run.",
    });
    await loginAccount(page, users.artistUser, DEMO_PASSWORD, { force: true });
    await openArtistPosts(page, users.artistUser);
    await snap(page, "06-artist-create-post");
    await expect(page.getByText(users.postTitle).first()).toBeVisible({ timeout: 15000 });
  });

  test("fan sees uploaded track on artist page", async ({ page }) => {
    await loginAccount(page, users.fanUser);
    await page.goto(`/?artist=${users.artistUser}`);
    await expect(page.getByText(users.trackTitle).first()).toBeVisible({ timeout: 15000 });
    await snap(page, "07-fan-sees-track");
  });
});

test.describe("Discovery Ads", () => {
  test("promotions wallet exposes fair-discovery invariants", async ({ request }) => {
    const response = await request.get(`${API}/promotions/wallet/`);
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.invariants?.max_budget).toBe("100.00");
    expect(data.invariants?.no_bidding).toBe(true);
    expect(data.tagline).toContain("audience decides");
  });

  test("artist can open promote page", async ({ page }) => {
    await loginAccount(page, users.artistUser);
    await page.goto("/?page=promote");
    await expect(page.getByRole("heading", { name: "Promote your release" })).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/audience decides what spreads next/i)).toBeVisible();
    await snap(page, "08-artist-promote-page");
  });
});

test.afterAll(() => {
  const reportPath = path.join(SCREENSHOT_DIR, "beta-run.json");
  fs.writeFileSync(
    reportPath,
    JSON.stringify(
      {
        generatedAt: new Date().toISOString(),
        users,
        accounts: ALL_BETA_ACCOUNTS.map(({ username, label }) => ({ username, label })),
        screenshotsDir: SCREENSHOT_DIR,
      },
      null,
      2
    )
  );
});
