/**
 * Aggregator for the persona-flow helper modules.
 *
 * Persona-flow modules (biber, admin, guest) `require("./utils")` to
 * pull every helper through a single import; Node resolves this to
 * `personas/utils/index.js` and exposes every helper through this
 * aggregator.
 */

const env = require("./env");
const keycloak = require("./keycloak");
const dashboard = require("./dashboard");
const logout = require("./logout");
const landing = require("./landing");
const prometheus = require("./prometheus");
const matomo = require("./matomo");
const csp = require("./csp");
const interaction = require("./interaction");

module.exports = {
  ...env,
  ...keycloak,
  ...dashboard,
  ...logout,
  ...landing,
  ...prometheus,
  ...matomo,
  ...csp,
  ...interaction,
};
