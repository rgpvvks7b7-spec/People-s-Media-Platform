import base from "./playwright.config.js";

export default {
  ...base,
  testMatch: /qa-audit\.spec\.js/,
  workers: 1,
};
