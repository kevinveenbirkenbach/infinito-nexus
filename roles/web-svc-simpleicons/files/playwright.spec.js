const { test, expect } = require("@playwright/test");

test.use({
  ignoreHTTPSErrors: true
});

function decodeDotenvQuotedValue(value) {
  if (typeof value !== "string" || value.length < 2) {
    return value;
  }

  if (!(value.startsWith('"') && value.endsWith('"'))) {
    return value;
  }

  const encoded = value.slice(1, -1);

  try {
    return JSON.parse(`"${encoded}"`).replace(/\$\$/g, "$");
  } catch {
    return encoded.replace(/\$\$/g, "$");
  }
}

function normalizeBaseUrl(value) {
  return decodeDotenvQuotedValue(value || "").replace(/\/$/, "");
}

function contentTypeOf(response) {
  return response.headers()["content-type"] || "";
}

function expectOrigin(url, expectedOrigin, label) {
  expect(new URL(url).origin, label).toBe(expectedOrigin);
}

function expectLandingPageText(body) {
  const normalized = body.toLowerCase();

  expect(
    normalized,
    "Expected the Simple Icons landing page to expose README or provider content on the Simple Icons domain"
  ).toMatch(/simple icons|simpleicons\.org|provided by/);
}

const appBaseUrl = normalizeBaseUrl(process.env.APP_BASE_URL || "");
const knownIconSlug = decodeDotenvQuotedValue(process.env.KNOWN_ICON_SLUG || "keycloak");

test("simpleicons serves keycloak assets directly on its own domain", async ({ request }) => {
  expect(appBaseUrl, "APP_BASE_URL must be set in the Playwright env file").toBeTruthy();
  expect(knownIconSlug, "KNOWN_ICON_SLUG must be set in the Playwright env file").toBeTruthy();

  const expectedOrigin = new URL(appBaseUrl).origin;

  const landingResponse = await request.get(appBaseUrl, { maxRedirects: 0 });
  const landingStatus = landingResponse.status();

  expect(
    landingStatus === 200 || (landingStatus >= 301 && landingStatus <= 302),
    `Expected the Simple Icons landing page to return HTTP 200 or a redirect (301/302), got ${landingStatus}`
  ).toBe(true);

  if (landingStatus === 200) {
    expectOrigin(
      landingResponse.url(),
      expectedOrigin,
      "Expected the Simple Icons landing page to stay on icon.infinito.example when no redirect is configured"
    );
    const landingBody = await landingResponse.text();
    expect(contentTypeOf(landingResponse)).toMatch(/text\/html|text\/plain/);
    expectLandingPageText(landingBody);
  } else {
    const location = landingResponse.headers()["location"];
    expect(location, "Expected the redirect to include a Location header").toBeTruthy();
  }

  const svgResponse = await request.get(`${appBaseUrl}/${knownIconSlug}.svg`);
  expect(svgResponse.status(), `Expected ${knownIconSlug}.svg to return HTTP 200`).toBe(200);
  expectOrigin(
    svgResponse.url(),
    expectedOrigin,
    `Expected ${knownIconSlug}.svg to stay on the Simple Icons domain instead of redirecting elsewhere`
  );
  expect(contentTypeOf(svgResponse)).toContain("image/svg+xml");
  const svgBody = await svgResponse.text();
  expect(svgBody).toContain("<svg");
  expect(svgBody).toContain("<path");

  const pngResponse = await request.get(`${appBaseUrl}/${knownIconSlug}.png?size=64`);
  expect(pngResponse.status(), `Expected ${knownIconSlug}.png to return HTTP 200`).toBe(200);
  expectOrigin(
    pngResponse.url(),
    expectedOrigin,
    `Expected ${knownIconSlug}.png to stay on the Simple Icons domain instead of redirecting elsewhere`
  );
  expect(contentTypeOf(pngResponse)).toContain("image/png");
  const pngBody = await pngResponse.body();
  expect(Buffer.compare(pngBody.subarray(0, 8), Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]))).toBe(0);
  expect(pngBody.length, "Expected the PNG route to return a non-empty image").toBeGreaterThan(100);

  const missingIconResponse = await request.get(`${appBaseUrl}/definitely-not-a-real-icon.svg`, { failOnStatusCode: false });
  expect(missingIconResponse.status(), "Expected unknown icons to return HTTP 404").toBe(404);
  expectOrigin(
    missingIconResponse.url(),
    expectedOrigin,
    "Expected missing icons to stay on the Simple Icons domain instead of redirecting elsewhere"
  );
  expect(await missingIconResponse.text()).toContain("Icon not found");
});
