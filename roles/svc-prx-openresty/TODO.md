# TODO — svc-prx-openresty

## lua-resty-prometheus — ongoing maintenance and security

**Context:**
The three Lua files that enable Prometheus metrics inside OpenResty
(`prometheus.lua`, `prometheus_resty_counter.lua`, `prometheus_keys.lua`)
are downloaded at Docker build time from the infinito-nexus org fork:

  https://github.com/infinito-nexus/nginx-lua-prometheus

Forked from https://github.com/knyar/nginx-lua-prometheus — a third-party
Prometheus exporter for Nginx written in Lua, compatible with OpenResty via
lua-nginx-module. Not an official OpenResty project, but distributed via GitHub
and OPM and used as a reference implementation in community and production
OpenResty deployments.

Using the org fork means only infinito-nexus org members can push to it —
the supply chain trust concern (dependency on an individual's account) is resolved.

---

### Task 1 — Keep fork in sync with upstream

Periodically check upstream for new releases and merge them into the fork
**after reviewing the diff for any breaking changes or vulnerabilities**.

Upstream releases: https://github.com/knyar/nginx-lua-prometheus/releases

---

### Task 2 — Security scan the Lua code

Even though the fork is under org control, the Lua code itself may contain
vulnerabilities (logic bugs, unsafe string handling, etc.). The files are small
enough for a manual review, but automated scanning should also be considered.

Options:
- **`luacheck`** — static analyser for Lua. Catches undefined globals, unused
  variables, and common bugs. Does not do security-specific analysis but is a
  good baseline. Run: `luacheck roles/svc-prx-openresty/` (requires luacheck installed).
- **Manual review** — the three files are short (~300 lines total). A one-time
  read-through when pulling upstream changes is feasible and recommended.
- **GitHub Dependabot / security advisories** — watch the upstream repo
  (https://github.com/knyar/nginx-lua-prometheus) for any reported CVEs or
  security advisories and merge fixes into the fork promptly.

---

### Task 3 — Consider pinning to a tag inside the fork

Currently the URLs point to `master` of the fork. Since the org controls the
fork this is safe, but pinning to a specific commit or tag inside the fork
makes it explicit which version is running and simplifies auditing.
