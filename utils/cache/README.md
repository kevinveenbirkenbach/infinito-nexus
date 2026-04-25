# Cache Helpers 💾

This package contains the in-process cache layers Infinito.Nexus uses to keep CLI tools, lookup plugins, and Ansible filters fast without re-reading or re-merging the same data multiple times per Python process.

## Modules 🧭

| Module | Caches |
|---|---|
| [yaml.py](yaml.py) | A single YAML file's parsed root, keyed by absolute path. |
| [data.py](data.py) | Aggregated runtime data per `roles_dir` (merged applications, users, domains, variants), plus templar-rendered merges keyed by inventory signature. |

## When To Use Which 🎯

- Use `utils.cache.yaml.load_yaml(path)` (or `load_yaml_any(path)` when the YAML root is a list or scalar) whenever a CLI tool, filter, or library reads individual YAML files where the same path MAY be touched repeatedly within a single invocation.
- Use the cached getters in `utils.cache.data` (`get_application_defaults`, `get_variants`, `get_user_defaults`, `get_merged_applications`, `get_merged_users`, `get_merged_domains`) whenever you need the aggregated, optionally templar-rendered application/user/domain payload that lookup plugins expose at runtime.

The two layers are orthogonal: `yaml.py` caches "this file's parsed root", `data.py` caches "this aggregated, rendered payload". They do not invalidate each other and MAY both be active at the same time.

## Lifetime 🕒

Both layers are process-wide in-process caches. They intentionally do NOT track on-disk file mtimes; CLI tools are short-lived and the assumption "the on-disk file does not change while my process runs" holds. The single exception is `utils.cache.yaml.dump_yaml`, which writes through and evicts the cached entry for the path it just wrote so a tool that edits a file mid-run sees the new content on the next read.

## Test-Only Helpers 🧪

Both modules expose a `_reset_cache_for_tests()` function. Unit tests that exercise the cached paths MUST call it in `setUp` to guarantee clean state across test cases.

## Design Guidelines 📐

- You MUST NOT introduce a third parallel cache for the same concern. If you need to cache a derived shape, add a getter to `data.py` that builds on the existing primitives.
- You SHOULD prefer the explicit cached getter over re-implementing the same memoisation in a calling module.
- You MUST NOT mutate values returned by `utils.cache.yaml.load_yaml`. The same dict instance is returned to every caller; callers that need to mutate MUST `copy.deepcopy()` the result first. Each `data.py` getter documents whether it returns a fresh deep copy or the cached instance; respect that contract.
- You MUST keep dependencies inside this package minimal. Cache primitives should remain importable from filter plugins, lookup plugins, and CLI tools without dragging in heavy dependencies.

## Example Imports ✍️

```python
from utils.cache.yaml import load_yaml, load_yaml_any
from utils.cache.data import (
    get_application_defaults,
    get_merged_applications,
    get_variants,
)
```
