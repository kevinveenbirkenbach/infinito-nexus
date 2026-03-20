# Missing Resolve Scripts

This directory contains resolver scripts for detecting missing derived artifacts and release metadata.

- 🔎 Check whether expected CI or release images are still missing
- 🏷️ Resolve the highest version tag that still needs release backfill
- 🗂️ Keep missing-state lookup logic grouped separately from general resolvers

The scope of this folder is missing-state resolution.
Image build, release, and workflow orchestration should stay in their dedicated script or workflow locations.
