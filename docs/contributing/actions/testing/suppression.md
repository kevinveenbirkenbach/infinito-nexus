# Suppression Markers 🚫

The unified `# noqa` / `# nocheck` syntax that suppresses individual
checks across the infinito-nexus test suite.

You MUST use these markers only when the check genuinely does not apply.
You MUST NOT use them to silence legitimate issues.

## Grammar 📐

A suppression marker is a comment carrying one or more rule keys:

```
<comment-prefix> (noqa|nocheck): <rule>(, <rule>)*
```

Rules:

- `noqa` and `nocheck` are synonyms. By convention, use `noqa` for code-level
  lints (analogous to flake8 / ruff) and `nocheck` for repository-content
  checks (URLs, image versions, file size, run-once schema). Either keyword
  works for any rule; the test does not enforce which one is used.
- The keyword is matched **case-insensitively**.
- `<rule>` is a kebab-case identifier from the catalog below.
- Multiple rules MAY be combined on one comment, comma-separated:
  `# noqa: shared, email`.

Accepted comment prefixes (so the marker fits any file format that the test
scans):

| Prefix       | Use in                                  |
| ------------ | --------------------------------------- |
| `#`          | Python, YAML, shell, conf, INI, …       |
| `//`         | JS, JSONC, …                            |
| `{# … #}`    | Jinja2 templates                        |
| `<!-- … -->` | HTML, Markdown                          |

Implementation: [utils/annotations/suppress.py](../../../../utils/annotations/suppress.py).

## Position semantics 📍

The placement rule is per check. The catalog column "Position" uses these
labels:

- **same line**: the marker MUST be on the same line as the construct
  it suppresses.
- **line above**: the marker MUST be on the immediately preceding
  non-empty line. Blank lines between the marker and the construct
  break the association.
- **same or above**: either of the above is accepted.
- **comment block above**: the marker may sit on any line in a
  contiguous comment block above the construct (no blank line between
  marker and construct).
- **head (first 30 lines)**: the marker MAY appear anywhere in the
  first 30 lines of the file. Used for file-level opt-outs that should
  stay visible at the top of the file.
- **anywhere**: the marker may appear on any line of the file. Used
  for whole-file opt-outs whose semantics legitimately apply to the
  entire file.

## Catalog 📚

| Rule                | Position            | Affected test                                                                                                                | Effect                                                                                                          |
| ------------------- | ------------------- | ---------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `url`               | same or above       | [test_urls_reachable.py](../../../../tests/external/repository/test_urls_reachable.py)                                       | Skips probing the literal HTTP(S) URL. Use for CDN roots and API base URLs that return 4xx without a path.       |
| `docker-version`    | line above          | [test_image_versions.py](../../../../tests/external/docker/test_image_versions.py)                                           | Skips the live version-update warning for that image's `version:` key.                                          |
| `direct-yaml`       | same line / span    | [test_no_direct_yaml_calls.py](../../../../tests/lint/repository/test_no_direct_yaml_calls.py)                               | Allows the marked `yaml.safe_load` / `safe_dump` call to bypass `utils.cache.yaml`.                              |
| `shared`            | comment block above | [test_service_shared_consistency.py](../../../../tests/lint/ansible/test_service_shared_consistency.py)                     | Marks a service whose `enabled: true` legitimately does not require `shared: true`.                              |
| `email`             | line above          | [test_web_app_email_integration.py](../../../../tests/lint/ansible/roles/test_web_app_email_integration.py)                 | Suppresses the missing-email-integration warning when paired with `enabled: false` and `shared: false`.          |
| `file-size`         | head (first 30 lines) | [test_python_file_size.py](../../../../tests/lint/repository/test_python_file_size.py)                                     | Opts the entire `.py` file out of the 500-line cap.                                                              |
| `run-once`          | anywhere            | [test_run_once_tags.py](../../../../tests/lint/ansible/test_run_once_tags.py), [test_schema.py](../../../../tests/integration/roles/run_once/test_schema.py) | Marks a role's `tasks/main.yml` as intentionally re-runnable; skips both the run-once tag check and the suffix check. |
| `run-once-suffix`   | same line           | [test_schema.py](../../../../tests/integration/roles/run_once/test_schema.py)                                                | Allows a single `when:` item to reference a `run_once_<other>` flag whose suffix differs from the current role.   |

## Examples 💡

`url`, on the line carrying the literal URL or on the line above it:

```sh
ensure_proxy_repo raw raw-packagist "$(... https://repo.packagist.org/ ...)"  # nocheck: url
```

```yaml
# nocheck: url
api_base_url: "https://example.org/v1"
```

`docker-version`, directly above a `version:` key:

```yaml
service_x:
  # nocheck: docker-version
  version: "4.5"
```

`direct-yaml`, anywhere on the call's physical line or on any line
spanned by the multi-line call:

```python
data = yaml.safe_load(text)  # noqa: direct-yaml
```

`shared`, somewhere in the comment block immediately above a service key:

```yaml
# This service is inherently role-local.
# noqa: shared
my_local_service:
  enabled: true
```

`email`, directly above the `email:` block, paired with both flags false:

```yaml
# noqa: email
email:
  enabled: false
  shared: false
```

`file-size`, at the top of a long Python file:

```python
"""Module docstring."""
# nocheck: file-size  (single-host orchestration script ships as one file)
```

`run-once`, at the top of a role's `tasks/main.yml`:

```yaml
# nocheck: run-once

- name: ...
```

`run-once-suffix`, on the exact `when:` list-item line:

```yaml
when:
  - run_once_svc_db_openldap is not defined   # noqa: run-once-suffix
```

## Adding a new rule 🆕

1. Pick a kebab-case `<rule>` identifier.
2. Decide which position semantic from the list above fits the check.
3. Use the `is_suppressed_at` / `is_suppressed_in_head` /
   `is_suppressed_anywhere` helpers from
   [utils/annotations/suppress.py](../../../../utils/annotations/suppress.py)
   in your test. Do NOT roll a new regex.
4. Add the rule to the catalog table on this page.
