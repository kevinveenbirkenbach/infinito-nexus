import os
import sys
import unittest
import tempfile
import shutil
import yaml
from collections import OrderedDict

# Add cli/ to import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..", "cli/setup/")))

import users

class TestGenerateUsers(unittest.TestCase):
    def test_build_users_auto_increment_and_overrides(self):
        defs = {
            'alice': {},
            'bob': {'uid': 2000, 'email': 'bob@custom.com', 'description': 'Custom user'},
            'carol': {}
        }
        build = users.build_users(
            defs=defs,
            primary_domain='example.com',
            start_id=1001,
            become_pwd='pw'
        )
        # alice should get uid/gid 1001
        self.assertEqual(build['alice']['uid'], 1001)
        self.assertEqual(build['alice']['gid'], 1001)
        self.assertEqual(build['alice']['email'], 'alice@example.com')
        # bob overrides
        self.assertEqual(build['bob']['uid'], 2000)
        self.assertEqual(build['bob']['gid'], 2000)
        self.assertEqual(build['bob']['email'], 'bob@custom.com')
        self.assertIn('description', build['bob'])
        # carol should get next free id = 1002
        self.assertEqual(build['carol']['uid'], 1002)
        self.assertEqual(build['carol']['gid'], 1002)

    def test_build_users_default_lookup_password(self):
        """
        When no 'password' override is provided,
        the become_pwd lookup template string must be used as the password.
        """
        defs = {'frank': {}}
        lookup_template = '{{ lookup("password", "/dev/null length=42 chars=ascii_letters,digits") }}'
        build = users.build_users(
            defs=defs,
            primary_domain='example.com',
            start_id=1001,
            become_pwd=lookup_template
        )
        self.assertEqual(
            build['frank']['password'],
            lookup_template,
            "The lookup template string was not correctly applied as the default password"
        )

    def test_build_users_override_password(self):
        """
        When a 'password' override is provided,
        that custom password must be used instead of become_pwd.
        """
        defs = {'eva': {'password': 'custompw'}}
        lookup_template = '{{ lookup("password", "/dev/null length=42 chars=ascii_letters,digits") }}'
        build = users.build_users(
            defs=defs,
            primary_domain='example.com',
            start_id=1001,
            become_pwd=lookup_template
        )
        self.assertEqual(
            build['eva']['password'],
            'custompw',
            "The override password was not correctly applied"
        )


    def test_build_users_duplicate_override_uid(self):
        defs = {
            'u1': {'uid': 1001},
            'u2': {'uid': 1001}
        }
        with self.assertRaises(ValueError):
            users.build_users(defs, 'ex.com', 1001, 'pw')

    def test_build_users_shared_gid_allowed(self):
        # Allow two users to share the same GID when one overrides gid and the other uses that as uid
        defs = {
            'a': {'uid': 1500},
            'b': {'gid': 1500}
        }
        build = users.build_users(defs, 'ex.com', 1500, 'pw')
        # Both should have gid 1500
        self.assertEqual(build['a']['gid'], 1500)
        self.assertEqual(build['b']['gid'], 1500)

    def test_build_users_duplicate_username_email(self):
        defs = {
            'u1': {'username': 'same', 'email': 'same@ex.com'},
            'u2': {'username': 'same'}
        }
        # second user with same username should raise
        with self.assertRaises(ValueError):
            users.build_users(defs, 'ex.com', 1001, 'pw')

    def test_dictify_converts_ordereddict(self):
        od = users.OrderedDict([('a', 1), ('b', {'c': 2})])
        result = users.dictify(OrderedDict(od))
        self.assertIsInstance(result, dict)
        self.assertEqual(result, {'a': 1, 'b': {'c': 2}})

    def test_load_user_defs_and_conflict(self):
        # create temp roles structure
        tmp = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(tmp, 'role1/users'))
            os.makedirs(os.path.join(tmp, 'role2/users'))
            # role1 defines user x
            with open(os.path.join(tmp, 'role1/users/main.yml'), 'w') as f:
                yaml.safe_dump({'users': {'x': {'email': 'x@a'}}}, f)
            # role2 defines same user x with same value
            with open(os.path.join(tmp, 'role2/users/main.yml'), 'w') as f:
                yaml.safe_dump({'users': {'x': {'email': 'x@a'}}}, f)
            defs = users.load_user_defs(tmp)
            self.assertIn('x', defs)
            # now conflict definition
            with open(os.path.join(tmp, 'role2/users/main.yml'), 'w') as f:
                yaml.safe_dump({'users': {'x': {'email': 'x@b'}}}, f)
            with self.assertRaises(ValueError):
                users.load_user_defs(tmp)
        finally:
            shutil.rmtree(tmp)

    def test_cli_users_sorted_by_key(self):
        """
        Ensure that default_users keys are written in alphabetical order.
        """
        import tempfile
        import subprocess
        from pathlib import Path

        tmpdir = Path(tempfile.mkdtemp())
        try:
            roles_dir = tmpdir / "roles"
            roles_dir.mkdir()

            # Create multiple roles with users in unsorted order
            for role, users_map in [
                ("role-zeta",  {"zeta":  {"email": "z@ex"}}),
                ("role-alpha", {"alpha": {"email": "a@ex"}}),
                ("role-mu",    {"mu":    {"email": "m@ex"}}),
                ("role-beta",  {"beta":  {"email": "b@ex"}}),
            ]:
                (roles_dir / role / "users").mkdir(parents=True, exist_ok=True)
                with open(roles_dir / role / "users" / "main.yml", "w") as f:
                    yaml.safe_dump({"users": users_map}, f)

            out_file = tmpdir / "users.yml"

            # Resolve script path like in other tests (relative to repo root)
            script_path = Path(__file__).resolve().parents[4] / "cli" / "setup" / "users.py"

            # Run generator
            result = subprocess.run(
                ["python3", str(script_path),
                "--roles-dir", str(roles_dir),
                "--output", str(out_file)],
                capture_output=True, text=True
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertTrue(out_file.exists(), "Output file was not created.")

            data = yaml.safe_load(out_file.read_text())
            self.assertIn("default_users", data)
            users_map = data["default_users"]
            keys_in_file = list(users_map.keys())

            # Expect alphabetical order
            self.assertEqual(
                keys_in_file, sorted(keys_in_file),
                msg=f"Users are not sorted alphabetically: {keys_in_file}"
            )
            # Sanity: all expected keys present
            for k in ["alpha", "beta", "mu", "zeta"]:
                self.assertIn(k, users_map)

        finally:
            shutil.rmtree(tmpdir)


    def test_cli_users_sorting_stable_across_runs(self):
        """
        Running the generator multiple times yields identical content (stable sort).
        """
        import tempfile
        import subprocess
        from pathlib import Path

        tmpdir = Path(tempfile.mkdtemp())
        try:
            roles_dir = tmpdir / "roles"
            roles_dir.mkdir()

            # Unsorted creation order on purpose
            cases = [
                ("role-d", {"duser": {"email": "d@ex"}}),
                ("role-a", {"auser": {"email": "a@ex"}}),
                ("role-c", {"cuser": {"email": "c@ex"}}),
                ("role-b", {"buser": {"email": "b@ex"}}),
            ]
            for role, users_map in cases:
                (roles_dir / role / "users").mkdir(parents=True, exist_ok=True)
                with open(roles_dir / role / "users" / "main.yml", "w") as f:
                    yaml.safe_dump({"users": users_map}, f)

            out_file = tmpdir / "users.yml"
            script_path = Path(__file__).resolve().parents[5] / "cli" / "setup" / "users.py"

            # First run
            r1 = subprocess.run(
                ["python3", str(script_path),
                "--roles-dir", str(roles_dir),
                "--output", str(out_file)],
                capture_output=True, text=True
            )
            self.assertEqual(r1.returncode, 0, msg=r1.stderr)
            content1 = out_file.read_text()

            # Touch dirs to shuffle filesystem mtimes
            for p in roles_dir.iterdir():
                os.utime(p, None)

            # Second run
            r2 = subprocess.run(
                ["python3", str(script_path),
                "--roles-dir", str(roles_dir),
                "--output", str(out_file)],
                capture_output=True, text=True
            )
            self.assertEqual(r2.returncode, 0, msg=r2.stderr)
            content2 = out_file.read_text()

            self.assertEqual(
                content1, content2,
                msg="Output differs between runs; user sorting should be stable."
            )
        finally:
            shutil.rmtree(tmpdir)

    def test_build_users_reserved_flag_propagated(self):
        """
        Ensure that the 'reserved' flag from the definitions is copied
        into the final user entries, and is not added for non-reserved users.
        """
        defs = {
            "admin": {"reserved": True},
            "bob": {},
        }

        build = users.build_users(
            defs=defs,
            primary_domain="example.com",
            start_id=1001,
            become_pwd="pw",
        )

        # Reserved user should carry the flag
        self.assertIn("reserved", build["admin"])
        self.assertTrue(build["admin"]["reserved"])

        # Non-reserved user should not have the flag at all
        self.assertNotIn("reserved", build["bob"])

    def test_cli_reserved_usernames_flag_sets_reserved_field(self):
        """
        Verify that --reserved-usernames marks given usernames as reserved
        in the generated YAML, and that existing definitions are preserved
        (only 'reserved' is added).
        """
        import tempfile
        import subprocess
        from pathlib import Path

        tmpdir = Path(tempfile.mkdtemp())
        try:
            roles_dir = tmpdir / "roles"
            roles_dir.mkdir()

            # Role with an existing user definition "admin"
            (roles_dir / "role-base" / "users").mkdir(parents=True, exist_ok=True)
            with open(roles_dir / "role-base" / "users" / "main.yml", "w") as f:
                yaml.safe_dump(
                    {
                        "users": {
                            "admin": {
                                "email": "admin@ex",
                                "description": "Admin from role",
                            }
                        }
                    },
                    f,
                )

            out_file = tmpdir / "users.yml"
            script_path = Path(__file__).resolve().parents[5] / "cli" / "setup" / "users.py"

            result = subprocess.run(
                [
                    "python3",
                    str(script_path),
                    "--roles-dir",
                    str(roles_dir),
                    "--output",
                    str(out_file),
                    "--reserved-usernames",
                    "admin,service",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertTrue(out_file.exists(), "Output file was not created.")

            data = yaml.safe_load(out_file.read_text())
            self.assertIn("default_users", data)
            users_map = data["default_users"]

            # "service" was created from the reserved list and must be reserved
            self.assertIn("service", users_map)
            self.assertTrue(users_map["service"].get("reserved", False))

            # "admin" existed before; its fields must remain unchanged,
            # but it must now be marked as reserved
            self.assertIn("admin", users_map)
            self.assertEqual(users_map["admin"]["email"], "admin@ex")
            self.assertEqual(users_map["admin"]["description"], "Admin from role")
            self.assertTrue(users_map["admin"].get("reserved", False))

        finally:
            shutil.rmtree(tmpdir)

if __name__ == '__main__':
    unittest.main()
