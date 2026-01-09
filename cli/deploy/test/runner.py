from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .compose import Compose
from .deps import apps_with_deps, resolve_run_after
from .logs import append_text, log_path, write_text
from .select import filter_allowed_server, filter_allowed_workstation


def _repo_root_from_here() -> Path:
    """
    Resolve repo root based on this file location.

    Path: <repo>/cli/deploy/test/runner.py
    parents:
      0 -> test
      1 -> deploy
      2 -> cli
      3 -> <repo>
    """
    return Path(__file__).resolve().parents[3]


def _get_invokable(compose: Compose) -> list[str]:
    # Capture output deterministically.
    r = compose.run(
        [
            "exec",
            "-T",
            "infinito",
            "sh",
            "-lc",
            "python3 -m cli.meta.applications.invokable",
        ],
        check=True,
        capture=True,
    )
    txt = (r.stdout or "").strip()
    return [line.strip() for line in txt.splitlines() if line.strip()]


def _tested_lifecycles_from_env() -> list[str]:
    """
    Lifecycles that are considered "tested" and therefore allowed to run.

    Compatible with the old bash runner behavior:
      TESTED_LIFECYCLES="alpha beta rc stable"
    """
    raw = os.environ.get("TESTED_LIFECYCLES", "alpha beta rc stable").strip()
    if not raw:
        return []
    # allow both space and comma-separated input
    raw = raw.replace(",", " ")
    return [t.strip() for t in raw.split() if t.strip()]


def _get_lifecycle_exclude(compose: Compose, tested_lifecycles: list[str]) -> list[str]:
    """
    Returns role names to exclude based on lifecycle_filter blacklist mode:
      exclude any role whose lifecycle is NOT in tested_lifecycles
    """
    if not tested_lifecycles:
        return []

    lifecycles_arg = " ".join(tested_lifecycles)

    # lifecycle_filter prints role names space-separated -> convert to newline
    r = compose.run(
        [
            "exec",
            "-T",
            "infinito",
            "sh",
            "-lc",
            f"python3 -m cli.meta.roles.lifecycle_filter blacklist {lifecycles_arg} | tr ' ' '\\n'",
        ],
        check=True,
        capture=True,
    )
    txt = (r.stdout or "").strip()
    return [line.strip() for line in txt.splitlines() if line.strip()]


def _ensure_vault_password_file(compose: Compose) -> None:
    # Keep as shell snippet (simple and robust)
    compose.exec(
        [
            "sh",
            "-lc",
            "mkdir -p /etc/inventories/github-ci && "
            "[ -f /etc/inventories/github-ci/.password ] || "
            "printf '%s\n' 'ci-vault-password' > /etc/inventories/github-ci/.password",
        ],
        check=True,
    )


def _create_inventory(compose: Compose, exclude_csv: str) -> None:
    # No sh -lc here: avoids quoting issues for exclude_csv.
    cmd = [
        "python3",
        "-m",
        "cli.create.inventory",
        "/etc/inventories/github-ci",
        "--host",
        "localhost",
        "--ssl-disabled",
        "--primary-domain",
        "infinito.localhost",
        "--vars-file",
        "inventory.sample.yml",
    ]

    if exclude_csv:
        cmd += ["--exclude", exclude_csv]

    compose.exec(
        cmd,
        check=True,
        workdir="/opt/src/infinito",
    )
    _ensure_vault_password_file(compose)


def _run_deploy(compose: Compose, deploy_type: str, extra_args: list[str]) -> int:
    cmd = [
        "python3",
        "-m",
        "cli.deploy.dedicated",
        "/etc/inventories/github-ci/servers.yml",
        "-p",
        "/etc/inventories/github-ci/.password",
        "-vv",
        "--assert",
        "true",
        "--debug",
        "--diff",
        "-T",
        deploy_type,
        *extra_args,
    ]
    r = compose.exec(cmd, check=False)
    return r.returncode


def run_test_plan(
    *,
    deploy_type: str,
    distro: str,
    no_cache: bool,
    missing_only: bool,
    only_app: str | None,
    logs_dir: Path,
    keep_stack_on_failure: bool,
) -> int:
    repo_root = _repo_root_from_here()
    compose = Compose(repo_root=repo_root, distro=distro)

    # Track final exit code so cleanup logic in finally is correct.
    exit_code = 0

    main_log = log_path(logs_dir, deploy_type, distro, "orchestrator")
    write_text(main_log, f"deploy_type={deploy_type}\ndistro={distro}\n")

    try:
        compose.build_infinito(no_cache=no_cache, missing_only=missing_only)
        compose.up()

        # critical: avoid race between "container is up" and "systemd is ready"
        compose.wait_for_systemd_ready(timeout_s=90)

        invokable = _get_invokable(compose)
        invokable_set = set(invokable)

        tested_lifecycles = _tested_lifecycles_from_env()
        lifecycle_exclude = _get_lifecycle_exclude(compose, tested_lifecycles)
        lifecycle_exclude_set = set(lifecycle_exclude) & invokable_set

        append_text(
            main_log,
            "\n".join(
                [
                    "",
                    f"tested_lifecycles={','.join(tested_lifecycles) if tested_lifecycles else '<none>'}",
                    f"lifecycle_exclude_count={len(lifecycle_exclude_set)}",
                    "",
                ]
            ),
        )

        if deploy_type == "workstation":
            allowed = filter_allowed_workstation(invokable)
            allowed_set = set(allowed)

            # Exclude everything not in allowed, plus lifecycle-based excludes
            exclude_set = (invokable_set - allowed_set) | lifecycle_exclude_set
            exclude = sorted(exclude_set)
            exclude_csv = ",".join(exclude)

            append_text(main_log, f"\nmode=workstation\nallowed_count={len(allowed)}\n")
            _create_inventory(compose, exclude_csv=exclude_csv)

            rc = _run_deploy(compose, "workstation", extra_args=[])
            exit_code = rc
            return rc

        # server mode: per-app deploy
        server_apps = filter_allowed_server(invokable)

        # Apply lifecycle gating to the server app list (so we don't try apps excluded by lifecycle)
        if lifecycle_exclude_set:
            server_apps = [a for a in server_apps if a not in lifecycle_exclude_set]

        if only_app:
            server_apps = [only_app]

        append_text(main_log, f"\nmode=server-per-app\napps={len(server_apps)}\n")

        for app in server_apps:
            deps = resolve_run_after(compose, app)
            include = apps_with_deps(app, deps_role_names=deps)

            include_set = set(include)

            # Always exclude lifecycle-blacklisted roles as well
            exclude_set = (invokable_set - include_set) | lifecycle_exclude_set
            exclude = sorted(exclude_set)
            exclude_csv = ",".join(exclude)

            per_app_log = log_path(logs_dir, deploy_type, distro, f"app-{app}")
            write_text(
                per_app_log,
                " ".join(
                    [
                        f"app={app}",
                        f"deps={','.join(deps) if deps else '<none>'}",
                        f"include={','.join(include)}",
                        f"exclude_count={len(exclude)}",
                        f"lifecycle_exclude_count={len(lifecycle_exclude_set)}",
                    ]
                )
                + "\n",
            )

            _create_inventory(compose, exclude_csv=exclude_csv)

            rc = _run_deploy(compose, "server", extra_args=["-i", app])
            if rc != 0:
                exit_code = rc
                append_text(
                    per_app_log,
                    "\n--- hint ---\n"
                    "Search workflow logs for the failing task output.\n"
                    f"Also run: INFINITO_DISTRO={distro} docker compose --profile ci logs --tail=200\n",
                )
                return rc

        exit_code = 0
        return 0

    except subprocess.CalledProcessError as exc:
        exit_code = exc.returncode
        append_text(main_log, f"\nERROR: {exc}\n")
        return exc.returncode
    except Exception as exc:
        exit_code = 1
        append_text(main_log, f"\nERROR: {exc}\n")
        return 1
    finally:
        should_keep = keep_stack_on_failure and exit_code != 0
        if should_keep:
            # do not tear down
            pass
        else:
            try:
                compose.down()
            except Exception:
                pass
