/**
 * Dashboard tile helpers: locate the role's tile (or a sibling
 * service's tile) on the canonical dashboard, click it, and verify
 * the resulting navigation lands on the expected canonical domain.
 *
 * The persona contract requires every authenticated entry to begin at
 * the dashboard tile (no direct URL navigation), so callers MUST use
 * these helpers rather than `page.goto(<canonical>)`.
 */

const { expect } = require("@playwright/test");

async function clickRoleTileFromDashboard(page, dashboardBaseUrl, canonicalDomain) {
  await page.goto(`${dashboardBaseUrl}/`, { waitUntil: "domcontentloaded" });

  const tile = page.locator(`a[href*="${canonicalDomain}"]`).first();
  await expect(tile, `role tile for ${canonicalDomain} must be present on the dashboard`).toBeVisible({
    timeout: 30_000,
  });

  const href = await tile.getAttribute("href");
  expect(href, "role tile must carry an href").toBeTruthy();
  expect(href, `role tile href must point at ${canonicalDomain}`).toContain(canonicalDomain);

  await tile.click();

  await expect
    .poll(() => page.url(), {
      timeout: 30_000,
      message: `Expected to land on ${canonicalDomain} after clicking role tile`,
    })
    .toContain(canonicalDomain);

  return href;
}

/**
 * Click a non-role tile (e.g. prometheus, matomo) on the dashboard so
 * personas can exercise navigation TO a sibling service from the
 * dashboard. Returns the host that was navigated to so callers can
 * assert further behaviour. Returns null if the tile is not visible.
 */
async function clickSiblingTileFromDashboard(page, dashboardBaseUrl, siblingBaseUrl) {
  if (!siblingBaseUrl) return null;
  await page.goto(`${dashboardBaseUrl}/`, { waitUntil: "domcontentloaded" });
  const host = new URL(siblingBaseUrl).hostname;
  const tile = page.locator(`a[href*="${host}"]`).first();
  const visible = await tile.isVisible({ timeout: 10_000 }).catch(() => false);
  if (!visible) return null;
  await tile.click();
  await expect
    .poll(() => page.url(), {
      timeout: 30_000,
      message: `Expected to land on ${host} after clicking sibling tile`,
    })
    .toContain(host);
  return host;
}

module.exports = { clickRoleTileFromDashboard, clickSiblingTileFromDashboard };
