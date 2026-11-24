"""`doctor --live` rules (engine/dojo/livecheck.py): pure functions of the resolved settings, no container engine."""
import hashlib
import unittest

from click.testing import CliRunner

from dojo import cli, livecheck
from dojo.doctor import FAIL, INFO, OK, WARN, Check

PUBLIC = {"PUBLIC_BASE_URL": "https://dojo.example.org", "LAB_HOST_IP": "0.0.0.0",
          "FACILITATOR_PASSWORD": "Zx9-long-enough-1", "FORGEJO_ADMIN_PASSWORD": "Qw8-long-enough-2",
          "TTYD_PASSWORD": "Ty7-long-enough-3", "STUDENT_PASSWORD_SEED": "seed-seed-seed-seed",
          "WEB_TERMINAL_MEM_LIMIT": "40g", "TERMINAL_FLAVOR": "web", "STUDENT_COUNT": "30"}


def run(env=None, operator=None, **kw):
    e = {**PUBLIC, **(env or {})}
    return livecheck.live_checks(e, operator if operator is not None else e, kw.pop("students", None), kw.pop("gate_pass", None), **kw)


def by_title(results, title):
    return [c for c in results if c.title == title]


class Secrets(unittest.TestCase):
    def test_a_clean_public_class_has_no_warning_or_failure(self):
        self.assertEqual([c for c in run() if c.level in (WARN, FAIL)], [])

    def test_empty_passwords_fail_when_public_and_warn_on_loopback(self):
        env = {"FACILITATOR_PASSWORD": "", "FORGEJO_ADMIN_PASSWORD": "  "}
        self.assertEqual(by_title(run(env), "Empty passwords")[0].level, FAIL)
        self.assertIn("FACILITATOR_PASSWORD", by_title(run(env), "Empty passwords")[0].detail)
        local = {**env, "PUBLIC_BASE_URL": "http://localhost:8080", "LAB_HOST_IP": "127.0.0.1"}
        self.assertEqual(by_title(run(local), "Empty passwords")[0].level, WARN)
        self.assertEqual(by_title(run(local), "Live")[0].level, INFO)

    def test_short_passwords_are_named(self):
        c = by_title(run({"TTYD_PASSWORD": "short"}), "Password length")[0]
        self.assertEqual(c.level, WARN)
        self.assertIn("TTYD_PASSWORD", c.detail)
        self.assertNotIn("FACILITATOR_PASSWORD", c.detail)

    def test_missing_seed_fails_when_public(self):
        self.assertEqual(by_title(run({"STUDENT_PASSWORD_SEED": ""}), "Student passwords")[0].level, FAIL)

    def test_facilitator_password_must_differ_from_student_secrets(self):
        c = by_title(run({"FACILITATOR_PASSWORD": "seed-seed-seed-seed"}), "Shared secrets")
        self.assertEqual(c[0].level, WARN)
        c = by_title(run({"STUDENT_PASSWORD_SEED": "", "STUDENT_PASSWORD": "Zx9-long-enough-1"}), "Shared secrets")
        self.assertEqual(len(c), 1)

    def test_gate_code_length(self):
        self.assertEqual(by_title(run(gate_pass="abc123"), "Access code")[0].level, WARN)
        self.assertEqual(by_title(run(gate_pass="abc12345"), "Access code"), [])
        self.assertEqual(by_title(run(), "Access code"), [])

    def test_ctf_dev_tokens(self):
        derived_empty = hashlib.sha256(b"ctf-range/control:").hexdigest()[:40]
        for bad in ("", "dev-ctf-control", derived_empty):
            self.assertEqual(by_title(run({"CTF_CONTROL_TOKEN": bad}), "CTF tokens")[0].level, FAIL, bad)
        real = hashlib.sha256(b"ctf-range/control:real-gateway-token").hexdigest()[:40]
        self.assertEqual(by_title(run({"CTF_CONTROL_TOKEN": real}), "CTF tokens"), [])
        self.assertEqual(by_title(run(), "CTF tokens"), [])   # not a CTF pack: the keys are absent


class Sizing(unittest.TestCase):
    def test_students_defaults_to_student_count_and_overrides(self):
        self.assertIn("need 1550", by_title(run(), "Pids for the class")[0].detail)       # 30 students + the facilitator, 50 each
        self.assertIn("need 550", by_title(run(students=10), "Pids for the class")[0].detail)

    def test_low_cap_is_information_because_the_start_raises_it(self):
        c = by_title(run({"WEB_TERMINAL_PIDS_LIMIT": "320"}, students=30), "Pids for the class")[0]
        self.assertEqual(c.level, INFO)
        self.assertIn("raises", c.detail)
        self.assertEqual(by_title(run({"WEB_TERMINAL_PIDS_LIMIT": "5000"}), "Pids for the class")[0].level, OK)

    def test_memory_warns_below_peak_and_ok_above(self):
        self.assertEqual(by_title(run({"WEB_TERMINAL_MEM_LIMIT": "8g"}), "Terminal memory")[0].level, WARN)
        self.assertEqual(by_title(run({"WEB_TERMINAL_MEM_LIMIT": "40g"}), "Terminal memory")[0].level, OK)
        z = run({"WEB_TERMINAL_MEM_LIMIT": "4g", "TERMINAL_FLAVOR": "zellij"})
        self.assertEqual(by_title(z, "Terminal memory")[0].level, OK)   # 31 x 100 MB

    def test_a_workshop_that_lowers_the_operators_value_is_named_with_its_file(self):
        env = {"WEB_TERMINAL_MEM_LIMIT": "1g"}
        r = run(env, operator={**PUBLIC, "WEB_TERMINAL_MEM_LIMIT": "40g"},
                origin_of=lambda k: "workshops/cloud-policy-as-code/workshop.env")
        c = by_title(r, "Sizing override")[0]
        self.assertEqual(c.level, FAIL)                     # 1 GB is under even the steady need of 31 students
        self.assertIn("workshops/cloud-policy-as-code/workshop.env", c.detail)
        r = run({"WEB_TERMINAL_MEM_LIMIT": "30g"}, operator={**PUBLIC, "WEB_TERMINAL_MEM_LIMIT": "40g"})
        self.assertEqual(by_title(r, "Sizing override")[0].level, WARN)   # lower, but still enough
        self.assertEqual(by_title(run(), "Sizing override"), [])


class Images(unittest.TestCase):
    def test_workshop_image_missing_warns_and_names_the_fix(self):
        c = by_title(run(workshop="tofu-basics", image_built=lambda tag: False), "Images built")[0]
        self.assertEqual(c.level, WARN)
        self.assertIn("topiary/web-terminal:tofu-basics", c.detail)
        self.assertIn("--build-only", c.fix)
        self.assertEqual(by_title(run(workshop="tofu-basics"), "Images built")[0].level, OK)
        self.assertEqual(by_title(run(), "Images built"), [])


class Escalation(unittest.TestCase):
    def test_only_the_named_warnings_become_failures(self):
        rs = [Check(WARN, "Resource limits"), Check(WARN, "HTTPS"), Check(WARN, "Student passwords"),
              Check(WARN, "Memory"), Check(INFO, "HTTPS")]
        livecheck.escalate(rs)
        self.assertEqual([c.level for c in rs], [FAIL, FAIL, FAIL, WARN, INFO])


class Command(unittest.TestCase):
    def test_students_and_pass_need_live(self):
        for args in (["--students", "5"], ["--pass", "abcdefgh"]):
            r = CliRunner().invoke(cli.cli, ["doctor", *args])
            self.assertEqual(r.exit_code, 2, r.output)
            self.assertIn("only apply with --live", r.output)


if __name__ == "__main__":
    unittest.main()
