# lookup_plugins/database.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

from module_utils.config_utils import get_app_conf
from module_utils.entity_name_utils import get_entity_name


class LookupModule(LookupBase):
    """
    Resolve database values for a given database_consumer_id.

    Usage:
      - {{ lookup('database', database_consumer_id) }}
      - {{ lookup('database', database_consumer_id, want='url_full') }}

    Inputs:
      - term[0] = database_consumer_id
      - reads these from Ansible vars:
          applications, ports, PATH_DOCKER_COMPOSE_INSTANCES

    Output keys (no prefixes):
      type, name, instance, host, container, username, password, port, env,
      url_jdbc, url_full, volume, image, version, reach_host
    """

    def run(
        self,
        terms: List[Any],
        variables: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> List[Any]:
        if not terms:
            raise AnsibleError(
                "lookup 'database': missing required term 'database_consumer_id'"
            )

        consumer_id = str(terms[0]).strip()
        if not consumer_id:
            raise AnsibleError(
                "lookup 'database': database_consumer_id must not be empty"
            )

        want = str(kwargs.get("want", "all"))

        vars_ = variables or self._templar.available_variables
        applications = self._require_var(vars_, "applications")
        ports = self._require_var(vars_, "ports")
        path_instances = self._require_var(vars_, "PATH_DOCKER_COMPOSE_INSTANCES")

        consumer_entity = get_entity_name(consumer_id)

        dbtype = get_app_conf(
            applications,
            consumer_id,
            "docker.services.database.type",
            strict=False,
            default="",
        )
        dbtype = (str(dbtype) if dbtype is not None else "").strip()

        # If no dbtype configured: keep behavior similar to your vars (mostly empty)
        if not dbtype:
            resolved = {
                "type": "",
                "name": consumer_entity,
                "instance": "",
                "host": "",
                "container": "",
                "username": consumer_entity,
                "password": "",
                "port": "",
                "env": "",
                "url_jdbc": "",
                "url_full": "",
                "volume": "",
                "image": "",
                "version": "",
                "reach_host": "127.0.0.1",
            }
            return [resolved if want == "all" else resolved.get(want, "")]

        central_enabled = bool(
            get_app_conf(
                applications,
                consumer_id,
                "docker.services.database.shared",
                strict=False,
                default=False,
            )
        )

        db_id = f"svc-db-{dbtype}"

        central_name = get_app_conf(
            applications,
            db_id,
            f"docker.services.{dbtype}.name",
            strict=False,
            default="",
            skip_missing_app=True,
        )
        central_name = (str(central_name) if central_name is not None else "").strip()

        name = consumer_entity
        instance = central_name if central_enabled else name
        host = central_name if central_enabled else "database"
        container = dbtype if central_enabled else f"{consumer_entity}-database"
        username = consumer_entity

        password = get_app_conf(
            applications,
            consumer_id,
            "credentials.database_password",
            strict=False,
            default="",
        )

        # ports.localhost.database[svc-db-<type>]
        port = ""
        try:
            port = ports["localhost"]["database"].get(db_id, "")
        except Exception:
            port = ""

        default_version = get_app_conf(
            applications,
            db_id,
            f"docker.services.{dbtype}.version",
            strict=False,
            default="",
            skip_missing_app=True,
        )

        version = get_app_conf(
            applications,
            consumer_id,
            "docker.services.database.version",
            strict=False,
            default=default_version,
        )

        # env path without docker_compose dict
        env_dir = f"{path_instances}{get_entity_name(consumer_id)}/.env/"
        env = f"{env_dir}{dbtype}.env"

        jdbc_scheme = dbtype if dbtype == "mariadb" else "postgresql"
        url_jdbc = f"jdbc:{jdbc_scheme}://{host}:{port}/{name}"
        url_full = f"{dbtype}://{username}:{password}@{host}:{port}/{name}"

        volume_prefix = f"{consumer_entity}_" if not central_enabled else ""
        volume = f"{volume_prefix}{host}"

        resolved = {
            "type": dbtype,
            "name": name,
            "instance": instance,
            "host": host,
            "container": container,
            "username": username,
            "password": password,
            "port": port,
            "env": env,
            "url_jdbc": url_jdbc,
            "url_full": url_full,
            "volume": volume,
            "image": dbtype,
            "version": version,
            "reach_host": "127.0.0.1",
        }

        return [resolved if want == "all" else resolved.get(want, "")]

    @staticmethod
    def _require_var(vars_: Dict[str, Any], key: str) -> Any:
        if key not in vars_:
            raise AnsibleError(
                f"lookup 'database': required variable '{key}' is not set"
            )
        return vars_[key]
