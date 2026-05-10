const { defineConfig } = require("@playwright/test");

const baseURL = process.env.APP_BASE_URL || "http://127.0.0.1";

const keepAll = (process.env.PLAYWRIGHT_KEEP_ALL || "").toLowerCase() === "true";

module.exports = defineConfig({
  testDir: "./tests",
  timeout: 300_000,
  retries: 2,
  workers: 1,
  outputDir: "/reports/test-results",
  reporter: [
    ["list"],
    ["junit", { outputFile: "/reports/playwright-junit.xml" }],
    ["html", { outputFolder: "/reports/playwright-report", open: "never" }]
  ],
  use: {
    baseURL,
    trace: keepAll ? "on" : "retain-on-failure",
    screenshot: keepAll ? "on" : "only-on-failure",
    video: keepAll ? "on" : "retain-on-failure"
  }
});
