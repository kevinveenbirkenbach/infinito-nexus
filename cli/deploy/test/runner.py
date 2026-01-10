from __future__ import annotations

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


def _create_inventory(
    compose: Compose,
    *,
    exclude_csv: str = "",
    include: list[str] | None = None,
) -> None:
    """
    Create CI inventory.

    - If `include` is provided: build inventory containing ONLY these application_ids.
    - Else: use `exclude_csv` to exclude a set of application_ids.
    """
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

    # cli.create.inventory has mutually exclusive --include/--exclude
    if include:
        cmd += ["--include", ",".join(include)]
    elif exclude_csv:
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

        if deploy_type == "workstation":
            allowed = filter_allowed_workstation(invokable)
            allowed_set = set(allowed)

            # Exclude everything not in allowed
            exclude_set = invokable_set - allowed_set
            exclude = sorted(exclude_set)
            exclude_csv = ",".join(exclude)

            append_text(main_log, f"\nmode=workstation\nallowed_count={len(allowed)}\n")
            _create_inventory(compose, exclude_csv=exclude_csv)

            rc = _run_deploy(compose, "workstation", extra_args=[])
            exit_code = rc
            return rc

        # server mode: per-app deploy
        server_apps = filter_allowed_server(invokable)

        if only_app:
            server_apps = [only_app]

        append_text(main_log, f"\nmode=server-per-app\napps={len(server_apps)}\n")

        for app in server_apps:
            deps = resolve_run_after(compose, app)
            deploy_ids = apps_with_deps(app, deps_role_names=deps)

            per_app_log = log_path(logs_dir, deploy_type, distro, f"app-{app}")
            write_text(
                per_app_log,
                " ".join(
                    [
                        f"app={app}",
                        f"deps={','.join(deps) if deps else '<none>'}",
                        f"deploy_ids={','.join(deploy_ids) if deploy_ids else '<none>'}",
                    ]
                )
                + "\n",
            )

            # Inventory should contain app + run_after deps
            _create_inventory(compose, include=deploy_ids)

            # Deploy app + deps
            rc = _run_deploy(compose, "server", extra_args=["-i", *deploy_ids])
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
