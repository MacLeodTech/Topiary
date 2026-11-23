"""The inline `dojo-check` wrapper in compose/terminal/Dockerfile: no argument or a target name goes to the
ctf-range checker, anything else to the achievements `dojo-check`. The script is cut out of the Dockerfile's
printf lines and run against stub programs, so a change to the Dockerfile is tested as written."""
import os
import re
import stat
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DOCKERFILE = os.path.join(HERE, "compose", "terminal", "Dockerfile")


def wrapper_lines():
    with open(DOCKERFILE) as f:
        text = f.read()
    block = text[text.index("printf '%s\\n'"):text.index("> /usr/local/bin/dojo-check;")]
    return re.findall(r"'([^']*)'", block)[1:]  # drop the '%s\n' format


class WrapperTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        script = "\n".join(wrapper_lines()) + "\n"
        # The two real programs live in /usr/local/bin; run the wrapper against stubs in the temp dir.
        script = script.replace("/usr/local/bin/", self.tmp.name + "/")
        self.wrapper = self.stub("dojo-check", script)
        self.stub("dojo-check-targets", '#!/bin/sh\necho "targets:$*"\n')
        self.stub("dojo-check-achievements", '#!/bin/sh\necho "achievements:$*"\n')

    def stub(self, name, body):
        path = os.path.join(self.tmp.name, name)
        with open(path, "w") as f:
            f.write(body)
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)
        return path

    def run_wrapper(self, *args):
        return subprocess.run([self.wrapper, *args], capture_output=True, text=True).stdout.strip()

    def test_the_script_was_found(self):
        self.assertTrue(wrapper_lines()[0].startswith("#!/bin/sh"))

    def test_no_argument_and_target_names_go_to_the_checker(self):
        self.assertEqual(self.run_wrapper(), "targets:")
        for target in ("customer-portal", "policy-bypass", "leaky-config"):
            self.assertEqual(self.run_wrapper(target, "--x"), f"targets:{target} --x")

    def test_everything_else_goes_to_achievements(self):
        for args in (("--shell",), ("--echo",), ("c1",), ("hint",)):
            self.assertEqual(self.run_wrapper(*args), "achievements:" + " ".join(args))


if __name__ == "__main__":
    unittest.main()
