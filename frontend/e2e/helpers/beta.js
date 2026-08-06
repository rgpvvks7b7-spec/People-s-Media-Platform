import fs from "fs";
import path from "path";
import { expect } from "@playwright/test";
import { ensureBetaFixtures } from "../fixtures/create-test-audio.js";

const FRONTEND = (process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:5173").replace(/\/$/, "");
export const API = process.env.PLAYWRIGHT_API_URL || `${FRONTEND}/api`;
const FRONTEND_API = `${FRONTEND}/api`;
const BACKEND_API = process.env.PLAYWRIGHT_BACKEND_API || "http://127.0.0.1:8000/api";
export const DEMO_PASSWORD = "demo12345";
export const SCREENSHOT_DIR = path.join(process.cwd(), "beta-screenshots");

const LOGGED_IN_SELECTOR = ".side-account, .account-chip, button[aria-label='Account menu']";

function loggedInIndicator(page) {
  return page.locator(LOGGED_IN_SELECTOR).first();
}

export function createBetaUsers(stamp = Date.now()) {
  return {
    fanUser: `beta_fan_${stamp}`,
    artistUser: `beta_artist_${stamp}`,
    artistStage: `Beta Artist ${stamp}`,
    trackTitle: `Beta Track ${stamp}`,
    postTitle: `Beta Post ${stamp}`,
  };
}

export async function waitForToast(page, text, timeout = 15000) {
  await expect(page.getByText(text, { exact: false }).first()).toBeVisible({ timeout });
}

async function getBrowserCsrfHeaders(page) {
  await page.request.get(`${FRONTEND_API}/accounts/current-user/`);
  const csrfToken = (await page.context().cookies()).find(cookie => cookie.name === "csrftoken")?.value;
  return csrfToken ? { "X-CSRFToken": csrfToken } : {};
}

async function loginBrowserViaApi(page, username, password = DEMO_PASSWORD) {
  let lastError = "";
  for (let attempt = 0; attempt < 4; attempt += 1) {
    await page.goto("/?page=profile");
    const csrfHeaders = await getBrowserCsrfHeaders(page);
    const loginResponse = await page.request.post(`${FRONTEND_API}/accounts/login/`, {
      headers: {
        "Content-Type": "application/json",
        ...csrfHeaders,
      },
      data: { username, password },
    });

    if (loginResponse.ok()) {
      return;
    }

    lastError = await loginResponse.text();
    const throttleMatch = lastError.match(/Expected available in (\d+) seconds/i);
    if (throttleMatch && attempt < 3) {
      await page.waitForTimeout((Number(throttleMatch[1]) + 1) * 1000);
      continue;
    }

    expect(loginResponse.ok(), lastError).toBeTruthy();
  }
}

async function logoutBrowserViaApi(page) {
  await page.evaluate(async () => {
    const csrf = document.cookie.match(/csrftoken=([^;]+)/)?.[1];
    await fetch("/api/accounts/logout/", {
      method: "POST",
      credentials: "include",
      headers: csrf ? { "X-CSRFToken": decodeURIComponent(csrf) } : {},
    });
  });
}

async function getBackendCsrfHeaders(page) {
  await page.request.get(`${BACKEND_API}/accounts/current-user/`);
  const csrfToken = (await page.context().cookies()).find(cookie => cookie.name === "csrftoken")?.value;
  return csrfToken ? { "X-CSRFToken": csrfToken } : {};
}

async function loginBackendViaApi(page, username, password = DEMO_PASSWORD) {
  await loginBrowserViaApi(page, username, password);
  const csrfHeaders = await getBrowserCsrfHeaders(page);
  const currentUserResponse = await page.request.get(`${FRONTEND_API}/accounts/current-user/`, {
    headers: csrfHeaders,
  });
  expect(currentUserResponse.ok(), await currentUserResponse.text()).toBeTruthy();
  const currentUserData = await currentUserResponse.json();
  expect(currentUserData.user?.username, await currentUserResponse.text()).toBe(username);
  return currentUserData;
}

async function postAuthedJson(page, path, data) {
  const csrfHeaders = await getBrowserCsrfHeaders(page);
  return page.request.post(`${FRONTEND_API}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...csrfHeaders,
    },
    data,
  });
}

export async function registerViaApi(page, { username, userType, extra = {} }) {
  await page.goto("/?page=profile");
  const displayName = extra.displayName || username.replace(/_/g, " ");
  const payload = {
    username,
    password: DEMO_PASSWORD,
    user_type: userType,
    display_name: displayName,
    email: extra.email || `${username}@example.com`,
    terms_accepted: true,
  };

  if (userType === "fan") {
    payload.favorite_genres = extra.favoriteGenres || "indie pop";
    payload.discovery_location = extra.discoveryLocation || "Melbourne";
  }
  if (userType === "host") {
    payload.discovery_location = extra.discoveryLocation || "Melbourne";
  }
  if (userType === "artist") {
    payload.stage_name = extra.stageName || displayName;
    payload.genre = extra.genre || "indie pop";
    payload.city = extra.city || "Melbourne";
    payload.professions = ["music"];
  }

  const csrfHeaders = await getBrowserCsrfHeaders(page);
  const registerResponse = await page.request.post(`${FRONTEND_API}/accounts/register/`, {
    headers: {
      "Content-Type": "application/json",
      ...csrfHeaders,
    },
    data: payload,
  });
  expect(registerResponse.ok(), await registerResponse.text()).toBeTruthy();

  const registerData = await registerResponse.json();
  expect(registerData.user?.username).toBe(username);
  return registerData;
}

async function apiAuthedUsername(page) {
  const response = await page.request.get(`${FRONTEND_API}/accounts/current-user/`);
  if (!response.ok()) return null;
  const data = await response.json();
  return data.user?.username || null;
}

async function browserLogout(page) {
  await page.evaluate(async () => {
    const csrf = document.cookie.match(/csrftoken=([^;]+)/)?.[1];
    await fetch("/api/accounts/logout/", {
      method: "POST",
      credentials: "include",
      headers: csrf ? { "X-CSRFToken": decodeURIComponent(csrf) } : {},
    });
  });
}

async function ensureLoggedOut(page) {
  await page.goto("/?page=profile");
  if (await loggedInIndicator(page).isVisible({ timeout: 2000 }).catch(() => false)) {
    await browserLogout(page);
    await page.reload();
  }
  await expect(page.locator("section.auth-panel form.auth-form")).toBeVisible({ timeout: 10000 });
}

export async function snap(page, name) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
  const filePath = path.join(SCREENSHOT_DIR, `${name}.png`);
  await page.screenshot({ path: filePath, fullPage: true });
  return filePath;
}

async function clearBrowserSession(page) {
  await page.context().clearCookies();
  await page.goto("/?page=profile");
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
}

async function persistBrowserSession(page, username) {
  await page.goto("/?page=home");
  const cookieOk = page.getByRole("button", { name: "OK" });
  if (await cookieOk.isVisible().catch(() => false)) {
    await cookieOk.click();
  }
  await expect.poll(async () => apiAuthedUsername(page), { timeout: 20000 }).toBe(username);
}

export async function loginAccount(page, username, password = DEMO_PASSWORD, { force = false } = {}) {
  await page.goto("/?page=profile");
  const authedUsername = await apiAuthedUsername(page);

  if (!force && authedUsername === username) {
    await persistBrowserSession(page, username);
    return;
  }

  if (authedUsername) {
    await clearBrowserSession(page);
    await expect.poll(async () => apiAuthedUsername(page), { timeout: 5000 }).toBeNull();
  }

  await loginBrowserViaApi(page, username, password);
  await expect.poll(async () => apiAuthedUsername(page), { timeout: 10000 }).toBe(username);
  await page.goto("/?page=home");
  await persistBrowserSession(page, username);
}

export async function getArtistOwnerId(page, username) {
  const response = await page.request.get(`${BACKEND_API}/artists/`);
  expect(response.ok()).toBeTruthy();
  const artists = await response.json();
  const artist = artists.find(entry => entry.owner_username === username);
  expect(artist, `Artist ${username} not found`).toBeTruthy();
  return artist.owner_id;
}

export async function followArtistViaApi(page, { fanUsername, artistUsername, password = DEMO_PASSWORD }) {
  await loginBackendViaApi(page, fanUsername, password);
  const artistId = await getArtistOwnerId(page, artistUsername);
  const response = await postAuthedJson(page, "/discovery/signal/", {
    artist_id: artistId,
    signal_type: "save",
  });
  expect(response.ok(), await response.text()).toBeTruthy();
}

export async function subscribeArtistViaApi(page, { fanUsername, artistUsername, password = DEMO_PASSWORD }) {
  await loginBackendViaApi(page, fanUsername, password);
  const artistId = await getArtistOwnerId(page, artistUsername);
  const response = await postAuthedJson(page, "/subscriptions/checkout/", {
    artist_id: artistId,
    profession: "music",
    monthly_amount: "1.00",
    billing_date: new Date().getDate(),
    share_email_with_artist: false,
  });
  expect(response.ok(), await response.text()).toBeTruthy();
}

export async function sendTipViaApi(page, { fanUsername, artistUsername, amount = "5.00", password = DEMO_PASSWORD }) {
  await loginBackendViaApi(page, fanUsername, password);
  const artistId = await getArtistOwnerId(page, artistUsername);
  const response = await postAuthedJson(page, "/subscriptions/tips/", {
    artist_id: artistId,
    profession: "music",
    amount,
  });
  expect(response.ok(), await response.text()).toBeTruthy();
}

export async function createPostViaApi(page, { artistUsername, title, body, password = DEMO_PASSWORD }) {
  await loginBackendViaApi(page, artistUsername, password);
  const csrfHeaders = await getBrowserCsrfHeaders(page);
  const response = await page.request.post(`${FRONTEND_API}/posts/create/`, {
    headers: csrfHeaders,
    multipart: {
      title,
      body,
    },
  });
  expect(response.ok(), await response.text()).toBeTruthy();
}

export async function uploadTrackViaApi(page, { title, audioPath, username, password = DEMO_PASSWORD }) {
  await loginBackendViaApi(page, username, password);
  const csrfHeaders = await getBrowserCsrfHeaders(page);
  const fileBuffer = fs.readFileSync(audioPath);
  const fileName = path.basename(audioPath);

  const response = await page.request.post(`${FRONTEND_API}/media/create/`, {
    headers: csrfHeaders,
    multipart: {
      title,
      audio_file: {
        name: fileName,
        mimeType: "audio/wav",
        buffer: fileBuffer,
      },
      profession: "music",
      ai_disclosure_level: "human_made",
      preview_enabled: "true",
      preview_seconds: "30",
    },
  });

  const responseText = await response.text();
  expect(response.ok(), responseText).toBeTruthy();
  expect(responseText).toContain("Track uploaded");
}

/**
 * Starts a listening party for the artist via the API, optionally attaching
 * one of their uploaded tracks by title, and returns the created session.
 */
export async function startListeningPartyViaApi(page, { artistUsername, title, trackTitle, accessMode = "public", password = DEMO_PASSWORD }) {
  await loginBackendViaApi(page, artistUsername, password);

  let trackId = null;
  if (trackTitle) {
    const mediaResponse = await page.request.get(`${FRONTEND_API}/media/`);
    expect(mediaResponse.ok(), await mediaResponse.text()).toBeTruthy();
    const mediaData = await mediaResponse.json();
    const tracks = Array.isArray(mediaData) ? mediaData : mediaData.results || [];
    trackId = tracks.find(track => track.title === trackTitle)?.id || null;
    expect(trackId, `Track ${trackTitle} not found`).toBeTruthy();
  }

  const response = await postAuthedJson(page, "/live/start/", {
    title,
    access_mode: accessMode,
    track_id: trackId,
  });
  expect(response.ok(), await response.text()).toBeTruthy();
  return (await response.json()).session;
}

export async function seedStoreCart(page, product = {}) {
  const item = {
    id: product.id ?? 4,
    title: product.title ?? "Luna Lane Logo Tee",
    price: product.price ?? "28.00",
    artist_username: product.artistUsername ?? "luna_lane",
    stage_name: product.stageName ?? "Luna Lane",
    product_type: product.productType ?? "merch",
  };
  await page.evaluate(cartItem => {
    localStorage.setItem("indiefund_store_cart", JSON.stringify([cartItem]));
  }, item);
  await page.goto("/?page=listen");
}

export async function registerAccount(page, { username, userType, extra = {} }) {
  await ensureLoggedOut(page);
  await registerViaApi(page, { username, userType, extra });
  await loginAccount(page, username, DEMO_PASSWORD, { force: true });
}

export async function openArtistStudio(page) {
  const nav = page.getByLabel("Primary navigation");
  const dashboardNav = nav.getByRole("button", { name: "Dashboard" });
  if (await dashboardNav.isVisible({ timeout: 3000 }).catch(() => false)) {
    await dashboardNav.click();
  }

  for (const label of ["Upload track", "+ Upload Track"]) {
    const button = page.getByRole("button", { name: label });
    if (await button.isVisible({ timeout: 2000 }).catch(() => false)) {
      await button.click();
      return;
    }
  }

  const openMyPage = page.getByRole("button", { name: "Open My Page" });
  if (await openMyPage.isVisible({ timeout: 5000 }).catch(() => false)) {
    await openMyPage.click();
    await page.getByRole("button", { name: "+ Upload Track" }).click({ timeout: 15000 });
    return;
  }

  await page.getByRole("button", { name: "Dashboard" }).click({ timeout: 10000 });
  await page.getByRole("button", { name: "Upload track" }).click({ timeout: 15000 });
}

export async function openArtistPosts(page, username) {
  await page.goto(`/?artist=${username}`);
  await page.getByRole("button", { name: "Feed", exact: true }).click();
}

export { ensureBetaFixtures };
