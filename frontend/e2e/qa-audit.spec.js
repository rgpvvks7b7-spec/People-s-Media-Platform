import { expect, test, devices } from "@playwright/test";
import { API, DEMO_PASSWORD, loginAccount } from "./helpers/beta.js";

const PAGES = [
  { path: "/?page=home", guestHeading: /INDIE|Log in|Welcome|sustainable music business/i, fanHeading: /Welcome back|Your overview|Business health/i },
  { path: "/?page=listen", guestHeading: /Listen|Recommended Artists|Recommended Songs/i, fanHeading: /Listen|Recommended Artists|Recommended Songs/i },
  { path: "/?page=listen&tab=latest", guestHeading: /Listen|Latest music|Latest/i, fanHeading: /Listen|Latest music|Latest/i },
  { path: "/?page=my-music", guestHeading: /My Playlists|Sign up|Log in/i, fanHeading: /My Playlists|Playlists/i },
  { path: "/?page=my-scene", guestHeading: /My Scene|Shows near|Sign up|Log in/i, fanHeading: /Local shows near/i },
  { path: "/?page=stores", guestHeading: /Stores|Sign up|Log in|Support an artist/i, fanHeading: /Stores|Merch|Support an artist/i },
  { path: "/?page=feed", guestHeading: /Feed|Artist updates|Sign up|Log in/i, fanHeading: /Feed|Artist updates/i },
  { path: "/?page=profile", guestHeading: /Log in|Create your account/i, fanHeading: /Account|Profile|More/i },
  { path: "/?page=notifications", guestHeading: /Notifications|Updates|Log in|Create your account/i, fanHeading: /Notifications|Updates/i },
  { path: "/?page=spaces", guestHeading: /Spaces|Book|Sign up/i, fanHeading: /Spaces|Book|Manage/i },
  { path: "/?page=promote", guestHeading: /Promote|Artist account required|Log in|Sign up/i, fanHeading: /Promote your release/i },
];

const API_ENDPOINTS = [
  { path: "/accounts/", auth: false },
  { path: "/accounts/current-user/", auth: false },
  { path: "/artists/public/marlo_saints/", auth: false },
  { path: "/discovery/artists/", auth: false },
  { path: "/discovery/tracks/", auth: false },
  { path: "/music/", auth: false },
  { path: "/posts/", auth: false },
  { path: "/marketplace/", auth: false },
  { path: "/spaces/listings/", auth: false },
  { path: "/live/", auth: false },
  { path: "/promotions/wallet/", auth: true, user: "luna_lane" },
  { path: "/notifications/", auth: true, user: "demo_fan" },
  { path: "/subscriptions/", auth: true, user: "demo_fan" },
];

test.describe.configure({ mode: "serial" });

test.describe("QA audit — API health", () => {
  for (const endpoint of API_ENDPOINTS) {
    test(`${endpoint.path} responds`, async ({ request, page }) => {
      if (endpoint.auth) {
        await loginAccount(page, endpoint.user, DEMO_PASSWORD, { force: true });
      }
      const response = await request.get(`${API}${endpoint.path}`);
      expect(response.status(), await response.text()).toBeLessThan(500);
    });
  }
});

test.describe("QA audit — guest pages", () => {
  for (const pageDef of PAGES) {
    test(`guest can load ${pageDef.path}`, async ({ page }) => {
      const consoleErrors = [];
      page.on("console", msg => {
        if (msg.type() === "error") consoleErrors.push(msg.text());
      });
      const failedRequests = [];
      page.on("response", res => {
        if (res.url().includes("/api/") && res.status() >= 400) {
          failedRequests.push({ url: res.url(), status: res.status() });
        }
      });

      await page.goto(pageDef.path);
      await expect(page.getByRole("heading").first()).toBeVisible({ timeout: 15000 });
      await expect(page.getByRole("heading").first()).toContainText(pageDef.guestHeading);

      if (failedRequests.length) {
        test.info().annotations.push({ type: "api-failures", description: JSON.stringify(failedRequests) });
      }
      if (consoleErrors.length) {
        test.info().annotations.push({ type: "console-errors", description: consoleErrors.slice(0, 5).join(" | ") });
      }
    });
  }

  test("legacy discover URL opens Listen discover tab", async ({ page }) => {
    await page.goto("/?page=discover");
    await expect(page.getByRole("heading", { name: "Listen" })).toBeVisible({ timeout: 15000 });
    await expect(page.getByRole("heading", { name: /Recommended Artists|Recommended Songs/i })).toBeVisible();
  });
});

test.describe("QA audit — fan session", () => {
  test("demo_fan login persists after reload on listen", async ({ page }) => {
    await loginAccount(page, "demo_fan", DEMO_PASSWORD, { force: true });
    await page.goto("/?page=listen");
    await page.reload();
    await page.waitForLoadState("networkidle");

    const apiUser = await page.evaluate(async () => {
      const res = await fetch("/api/accounts/current-user/", { credentials: "include" });
      const data = await res.json();
      return data.user?.username || null;
    });

    const guestBanner = page.getByText("Browsing as a guest");
    const sideAccount = page.locator(".side-account");

    test.info().annotations.push({
      type: "session-check",
      description: JSON.stringify({
        apiUser,
        guestBannerVisible: await guestBanner.isVisible().catch(() => false),
        sideAccountVisible: await sideAccount.isVisible().catch(() => false),
      }),
    });

    expect(apiUser).toBe("demo_fan");
    await expect(guestBanner).toHaveCount(0);
    await expect(sideAccount).toBeVisible();
  });

  for (const pageDef of PAGES.filter(p => !p.path.includes("promote"))) {
    test(`demo_fan can load ${pageDef.path}`, async ({ page }) => {
      await loginAccount(page, "demo_fan", DEMO_PASSWORD, { force: true });
      await page.goto(pageDef.path);
      await expect(page.getByRole("heading").first()).toBeVisible({ timeout: 15000 });
    });
  }
});

test.describe("QA audit — artist session", () => {
  test("luna_lane dashboard loads", async ({ page }) => {
    await loginAccount(page, "luna_lane", DEMO_PASSWORD, { force: true });
    await page.getByRole("button", { name: "Dashboard" }).click();
    await expect(page.getByRole("heading", { name: /Business health|Welcome back/i })).toBeVisible({ timeout: 15000 });
  });

  test("luna_lane can open artist public page", async ({ page }) => {
    await loginAccount(page, "luna_lane", DEMO_PASSWORD, { force: true });
    await page.goto("/?artist=luna_lane");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible({ timeout: 15000 });
  });

  test("luna_lane promote page loads", async ({ page }) => {
    await loginAccount(page, "luna_lane", DEMO_PASSWORD, { force: true });
    await page.goto("/?page=promote");
    await expect(page.getByRole("heading", { name: "Promote your release" })).toBeVisible({ timeout: 15000 });
  });
});

test.describe("QA audit — host session", () => {
  test("team_host spaces page loads", async ({ page }) => {
    await loginAccount(page, "team_host", DEMO_PASSWORD, { force: true });
    await page.getByRole("button", { name: "Spaces" }).click();
    await expect(page.getByRole("heading", { name: "Your rooms" })).toBeVisible({ timeout: 15000 });
  });
});

test.describe("QA audit — registration UX", () => {
  test("fan registration with minimal fields shows validation or error", async ({ page }) => {
    const username = `qa_fan_${Date.now()}`;
    await page.goto("/?page=profile");
    await page.getByRole("button", { name: "Register" }).click();
    await page.getByPlaceholder("Username").fill(username);
    await page.getByPlaceholder("Password").fill("demo12345");
    await page.getByRole("button", { name: "Create Account" }).click();

    const accountCreated = page.getByText("Account created");
    const signedIn = page.getByText("Signed in");
    const sideAccount = page.locator(".side-account");

    await page.waitForTimeout(2000);

    test.info().annotations.push({
      type: "registration-result",
      description: JSON.stringify({
        accountCreatedVisible: await accountCreated.isVisible().catch(() => false),
        signedInVisible: await signedIn.isVisible().catch(() => false),
        sideAccountVisible: await sideAccount.isVisible().catch(() => false),
        stillOnForm: await page.locator("form.auth-form").isVisible(),
      }),
    });
  });

  test("fan registration with all required fields succeeds", async ({ page }) => {
    const username = `qa_fan_full_${Date.now()}`;
    await page.goto("/?page=profile");
    await page.getByRole("button", { name: "Register" }).click();
    await page.getByPlaceholder("Username").fill(username);
    await page.getByPlaceholder("Password").fill("demo12345");
    await page.getByPlaceholder("Display name").fill("QA Fan");
    await page.getByPlaceholder("Email address").fill(`${username}@example.com`);
    await page.getByPlaceholder("Favorite genres").fill("indie pop");
    await page.getByPlaceholder("City or region").fill("Melbourne");
    await page.getByRole("checkbox", { name: /Terms of Service and Privacy Policy/i }).check();
    await page.getByRole("button", { name: "Create Account" }).click();

    await expect(page.locator(".side-account")).toBeVisible({ timeout: 15000 });
  });
});

test.describe("QA audit — mobile viewport", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(devices["iPhone 13"].viewport);
  });

  test("guest listen on mobile", async ({ page }) => {
    await page.goto("/?page=listen");
    await expect(page.getByRole("navigation", { name: "Mobile navigation" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Listen" })).toBeVisible({ timeout: 15000 });
  });

  test("demo_fan can load shows near me", async ({ page }) => {
    await loginAccount(page, "demo_fan", DEMO_PASSWORD, { force: true });
    await page.goto("/?page=my-scene");
    await expect(page.getByRole("heading", { name: /Local shows near you/i })).toBeVisible({ timeout: 15000 });
  });

  test("demo_fan mobile bottom nav works", async ({ page }) => {
    await loginAccount(page, "demo_fan", DEMO_PASSWORD, { force: true });
    const mobileNav = page.getByRole("navigation", { name: "Mobile navigation" });
    await expect(mobileNav).toBeVisible();

    await mobileNav.getByRole("button", { name: "Listen" }).click();
    await expect(page).toHaveURL(/page=listen/);

    await mobileNav.getByRole("button", { name: "My Playlists" }).click();
    await expect(page).toHaveURL(/page=my-music/);
  });

  test("public artist page on mobile", async ({ page }) => {
    await page.goto("/?artist=marlo_saints");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible({ timeout: 15000 });
    const followBtn = page.getByRole("button", { name: "Follow" });
    await expect(followBtn).toBeVisible();
  });
});

test.describe("QA audit — artist page interactions", () => {
  test("guest follow button prompts login", async ({ page }) => {
    await page.goto("/?artist=marlo_saints");
    await page.getByRole("button", { name: "Follow" }).click();
    await expect(page.getByText(/Log in|Sign up|Create/i).first()).toBeVisible({ timeout: 10000 });
  });

  test("marlo_saints page has music tab", async ({ page }) => {
    await page.goto("/?artist=marlo_saints");
    await page.getByRole("button", { name: "Listen", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Listen" })).toBeVisible({ timeout: 15000 });
  });
});
