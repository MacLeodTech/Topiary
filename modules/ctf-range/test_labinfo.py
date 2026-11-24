"""The Lab Info library teaches tools, never a lab's answer (CTF-D16, roadmap 6.1.2).

Mechanical half of the leak audit: no distinctive string a target's exploit/solve.py sends may appear in a primer, and
the technique-revealing phrases a hand read found once stay out. A primer may show how a tool behaves on a toy input;
it may not contain the payload, the field or the path that opens a lab.

Run: cd modules/ctf-range && python3 -B -m unittest test_labinfo
"""
import ast
import pathlib
import re
import unittest

HERE = pathlib.Path(__file__).resolve().parent
PRIMERS = sorted((HERE / "terminal" / "content" / "lab-info").glob("*.md"))
SOLVERS = sorted((HERE / "targets").glob("*/exploit/solve.py"))
# Generic web paths every HTTP primer uses as its toy example; they say nothing about a lab.
ALLOWED = {"/login", "/admin"}
MIME = re.compile(r"^[a-z]+/[a-z0-9.+-]+$")   # application/json and friends: every HTTP primer shows them
# Phrases a hand audit found in a primer and removed; each names a lab's technique.
BANNED = (r"' *OR *'1'='1", r"\bOR 1=1\b", r"UNION +SELECT", r"role=admin", r"169\.254\.169\.254", r"file:///etc", r"\.\./\.\./")
# A JSON "role" field is the shape the api-mass-assignment lab abuses, so no HTTP-tool primer uses one in an example.
# opa.md keeps its toy `input.role` policy: the policy-bypass lab has nothing to do with a role.
NO_ROLE_FIELD = re.compile(r"[\"']role[\"']|\brole=", re.I)
ROLE_OK = {"opa.md"}


def distinctive_literals(path):
    """Strings a solve script sends that are not plain words: they hold a quote, operator, path, dot or digit."""
    found = set()
    for n in ast.walk(ast.parse(path.read_text())):
        values = []
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            values.append(n.value)
        elif isinstance(n, ast.JoinedStr):
            values += [x.value for x in n.values if isinstance(x, ast.Constant) and isinstance(x.value, str)]
        for v in values:
            v = v.strip()
            if 6 <= len(v) <= 120 and "\n" not in v and re.search(r"[^A-Za-z _-]", v) and v not in ALLOWED and not MIME.match(v):
                found.add(v)
    return found


class LabInfoLeaks(unittest.TestCase):
    def test_there_is_something_to_check(self):
        self.assertGreaterEqual(len(PRIMERS), 10)
        self.assertGreaterEqual(len(SOLVERS), 10)

    def test_no_solve_payload_appears_in_a_primer(self):
        text = {p.name: p.read_text().lower() for p in PRIMERS}
        for solver in SOLVERS:
            for literal in distinctive_literals(solver):
                for name, body in text.items():
                    self.assertNotIn(literal.lower(), body, f"{name} contains {literal!r} from {solver.parent.parent.name}")

    def test_phrases_removed_by_the_audit_stay_out(self):
        for p in PRIMERS:
            body = p.read_text()
            for pattern in BANNED:
                self.assertIsNone(re.search(pattern, body, re.I), f"{p.name} matches {pattern}")

    def test_no_http_primer_shows_a_role_field(self):
        for p in PRIMERS:
            if p.name not in ROLE_OK:
                self.assertIsNone(NO_ROLE_FIELD.search(p.read_text()), f"{p.name} shows a role field")

    def test_the_checker_itself_sees_a_payload(self):
        # sqli-login sends this; if distinctive_literals stopped finding it the test above would pass vacuously.
        lits = distinctive_literals(HERE / "targets" / "sqli-login" / "exploit" / "solve.py")
        self.assertTrue(any("OR '1'='1'" in x for x in lits), lits)


if __name__ == "__main__":
    unittest.main()
