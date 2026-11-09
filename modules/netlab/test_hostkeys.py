import base64
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
import generate  # noqa: E402
import hostkeys  # noqa: E402


class Keys(unittest.TestCase):
    def test_rfc8032_vector(self):
        seed = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
        self.assertEqual(hostkeys.public_key(seed).hex(),
                         "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")

    def test_derivation_is_per_node_and_per_class_seed(self):
        a = hostkeys.host_seed("s", "pc-a-01")
        self.assertEqual(a, hostkeys.host_seed("s", "pc-a-01"))
        self.assertNotEqual(a, hostkeys.host_seed("s", "pc-a-02"))
        self.assertNotEqual(a, hostkeys.host_seed("t", "pc-a-01"))
        self.assertEqual(len(a), 32)

    @unittest.skipUnless(shutil.which("ssh-keygen"), "needs ssh-keygen")
    def test_private_pem_is_a_valid_openssh_key_with_the_same_public_half(self):
        seed = hostkeys.host_seed("s", "fw-m-03")
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "k")
            with open(path, "w") as f:
                f.write(hostkeys.private_pem(seed))
            os.chmod(path, 0o600)
            out = subprocess.run(["ssh-keygen", "-y", "-f", path], capture_output=True, text=True, check=True).stdout
        self.assertEqual(out.strip(), hostkeys.public_line(seed))


class KnownHosts(unittest.TestCase):
    def test_every_node_name_and_address_once(self):
        lines = hostkeys.known_hosts("s", 3).splitlines()
        self.assertEqual(len(lines), 3 * 8)
        self.assertIn(("pc-m-00,10.80.1.0 " + hostkeys.public_line(hostkeys.host_seed("s", "pc-m-00"))), lines)
        self.assertTrue(any(l.startswith("web-a-02,10.80.1.23 ") for l in lines))
        self.assertTrue(all(re.match(r"^[a-z]+-[ma]-\d\d,10\.80\.1\.\d+ ssh-ed25519 \S+$", l) for l in lines))

    def test_addresses_match_the_generator(self):
        for pod in (0, 1, 7):
            for b in "ma":
                for role in "pc sw fw web".split():
                    self.assertEqual(hostkeys.mgmt_ip(pod, b, role), generate.mgmt_ip(pod, b, role))

    def test_pods_from_env(self):
        self.assertEqual(hostkeys.pods_from_env({"STUDENT_COUNT": "3", "BOT_COUNT": "2"}), 6)

    def test_generated_node_gets_the_key_the_known_hosts_pins(self):
        text = generate.render({"STUDENT_COUNT": "1", "STUDENT_PASSWORD_SEED": "s"})
        m = re.search(r"container_name: \"netlab_pc_a_01\".*?HOST_KEY_B64=(\S+)", text, re.S)
        pem = base64.b64decode(m.group(1)).decode()
        self.assertEqual(pem, hostkeys.private_pem(hostkeys.host_seed("s", "pc-a-01")))
        self.assertEqual(text.count("HOST_KEY_B64="), text.count("ROOT_PASSWORD="))

    def test_terminal_copy_is_identical(self):
        with open(os.path.join(here, "hostkeys.py")) as a, open(os.path.join(here, "terminal", "hostkeys.py")) as b:
            self.assertEqual(a.read(), b.read())


if __name__ == "__main__":
    unittest.main()
