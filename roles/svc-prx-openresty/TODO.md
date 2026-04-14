# TODO — svc-prx-openresty

## Harden lua-resty-prometheus supply chain

**Context:**
The three Lua files that enable Prometheus metrics inside OpenResty
(`prometheus.lua`, `prometheus_resty_counter.lua`, `prometheus_keys.lua`)
are downloaded at Docker build time from:

  https://github.com/knyar/nginx-lua-prometheus

This is a third-party Prometheus exporter for Nginx written in Lua, compatible
with OpenResty via lua-nginx-module. It is not an official OpenResty project.
It is distributed via GitHub and OPM (OpenResty Package Manager) and used in
community and production OpenResty deployments as a reference implementation
for Prometheus instrumentation. There is no formal upstream endorsement by
OpenResty or CNCF — trust is based on open-source adoption, usage in community
examples, and long-term public availability.
See `vars/main.yml` for the full trust rationale.

**Current risk:**
The URLs point to the `master` branch, which is mutable — a different commit
could be served between two Docker builds without any visible change in the
Ansible config.

**Task:**
Decide on and implement one of the following hardening strategies:

1. **Pin to a release tag** — change `master` to a specific tag (e.g. `0.20240525`)
   in `vars/main.yml` and add SHA-256 checksum verification in the Dockerfile
   `RUN` step. Update deliberately when a new release is needed.
   Simple. No automation required. Same pattern as pinning Docker image versions.

2. **Vendor the files** — copy the three `.lua` files into
   `roles/svc-prx-openresty/files/lua/` and `COPY` them in the Dockerfile
   instead of downloading at build time. No internet required at build time.
   Requires a manual update process or Renovate custom datasource.

3. **Renovate automation** — configure Renovate with a custom regex datasource
   watching `knyar/nginx-lua-prometheus` GitHub releases to open automatic
   update PRs when a new tag appears (works with either option 1 or 2).

**Recommendation:** Start with option 1 (tag pin + checksum) as it requires
no tooling changes. Add option 3 later if Renovate is adopted project-wide.
