import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: /prelaunch\.spec\.js/,
  timeout: 60_000,
  fullyParallel: true,
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:5173",
  },
  webServer: process.env.PLAYWRIGHT_SKIP_WEBSERVER
    ? undefined
    : [
        {
          command: ".venv/bin/python manage.py runserver 127.0.0.1:8000",
          cwd: "../backend",
          url: "http://127.0.0.1:8000/api/health/",
          reuseExistingServer: false,
          timeout: 120_000,
          env: {
            ...process.env,
            DEBUG: "True",
            API_THROTTLE_ENABLED: "0",
            PLATFORM_MODE: "prelaunch",
          },
        },
        {
          command: "npm run dev -- --host 127.0.0.1 --port 5173",
          url: "http://127.0.0.1:5173",
          reuseExistingServer: false,
          timeout: 120_000,
          env: {
            ...process.env,
            VITE_API_URL: "/api",
            VITE_PLATFORM_MODE: "prelaunch",
          },
        },
      ],
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
