import base from "./playwright.config.js";

export default {
  ...base,
  testMatch: /checkout\.spec\.js/,
  workers: 1,
  retries: 1,
};
