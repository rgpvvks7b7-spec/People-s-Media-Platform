# Playwright examples

## Helper with JSDoc

```javascript
/**
 * Signs in through the auth panel and waits for the shell to load.
 * @param {import('@playwright/test').Page} page
 * @param {string} username
 * @param {string} password
 */
export async function loginAccount(page, username, password) {
  await page.goto("/");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page.getByRole("navigation")).toBeVisible();
}
```

## API + UI combined test

```javascript
test("artist can request a space booking", async ({ page, request }) => {
  await loginAccount(page, "artist1", "demo12345");
  await page.goto("/?page=spaces");
  await page.getByRole("button", { name: "Request booking" }).click();
  await expect(page.getByRole("heading", { name: /Request a show/i })).toBeVisible();
});
```

## Request fixture for backend checks

```javascript
test("accounts endpoint responds", async ({ request }) => {
  const response = await request.get("/api/accounts/");
  expect(response.ok()).toBeTruthy();
});
```

## test-id when roles are ambiguous

```jsx
<button data-testid="calendar-save-date" type="submit">Save Date</button>
```

```javascript
await page.getByTestId("calendar-save-date").click();
```
