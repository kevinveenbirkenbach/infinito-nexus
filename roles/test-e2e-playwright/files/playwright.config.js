const { defineConfig } = require("@playwright/test");

const baseURL = process.env.APP_BASE_URL || "http://127.0.0.1";

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
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure"
  }
});
