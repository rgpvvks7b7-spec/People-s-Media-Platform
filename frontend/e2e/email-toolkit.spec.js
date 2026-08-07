import { execFileSync } from "child_process";
import path from "path";
import { expect, test } from "@playwright/test";
import {
  DEMO_PASSWORD,
  createBetaUsers,
  loginAccount,
  registerAccount,
} from "./helpers/beta.js";

test.describe.configure({ mode: "serial" });

const stamp = Date.now();
const users = createBetaUsers(`mail_${stamp}`);

/**
 * Seeds N opted-in mailing contacts directly in Django for stable e2e setup.
 */
function seedMailingContacts({ artistUsername, count }) {
  const script = `
from django.contrib.auth import get_user_model
from artists.models import ArtistFanContact
User = get_user_model()
artist = User.objects.get(username=${JSON.stringify(artistUsername)})
for index in range(${Number(count)}):
    fan, _ = User.objects.get_or_create(
        username=f"mail_seed_${stamp}_{index}",
        defaults={
            "email": f"mail_seed_${stamp}_{index}@example.com",
            "user_type": User.FAN,
        },
    )
    if not fan.has_usable_password():
        fan.set_password(${JSON.stringify(DEMO_PASSWORD)})
        fan.save()
    contact, _ = ArtistFanContact.objects.get_or_create(fan=fan, artist=artist)
    contact.share(source=ArtistFanContact.MANUAL)
    contact.save()
print("ok", ArtistFanContact.objects.filter(artist=artist, email_shared=True).count())
`;
  const backendDir = path.resolve(process.cwd(), "../backend");
  const output = execFileSync(
    path.join(backendDir, ".venv/bin/python"),
    ["manage.py", "shell", "-c", script],
    { cwd: backendDir, encoding: "utf8" },
  );
  expect(output).toContain("ok");
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

  test("free artist with 10 contacts sees export nudge", async ({ page }) => {
    const artist = `mail_nudge_${stamp}`;
    await registerAccount(page, {
      username: artist,
      userType: "artist",
      extra: { stageName: "Nudge Artist" },
    });
    seedMailingContacts({ artistUsername: artist, count: 10 });
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
