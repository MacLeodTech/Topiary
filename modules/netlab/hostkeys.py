"""Deterministic SSH host keys for the netlab nodes, and the known_hosts file that pins them.

Students are root (with NET_ADMIN) on their own nodes, which share a management network with their pod (and with the
checker and the terminal), so a student could take over a node address in that pod and answer the checker's or the facilitator's SSH. Clients used
to ignore host keys. Now each node's ed25519 host key is derived from the class seed and the node's name:

    private seed = HMAC-SHA256(STUDENT_PASSWORD_SEED, "netlab-hostkey:<node name>")      (the 32-byte ed25519 seed)

so the generator (which hands the node its key), the checker, netlab-view and the terminal (which each write a
known_hosts) all compute the same keys offline, with no key distribution. Stdlib only (RFC 8032, pure Python): the
checker image is bare Alpine Python and the terminals have no internet. Only the public half is ever needed by a client.

Copies: this file lives in modules/netlab/, in terminal/hostkeys.py (the terminal image's build context is that folder)
and in the checker and view images (compose.yml). test_hostkeys.py fails if the terminal copy drifts.
"""
import base64
import hashlib
import hmac
import struct

MGMT_NET_BASE = "10.80."            # generate.py MGMT_NET_BASE
NODE_HOST_BASE = 10                 # generate.py NODE_HOST_BASE
ROLE_SLOT = {"pc": 0, "sw": 1, "fw": 2, "web": 3}
BRANCH_SLOT = {"m": 0, "a": 4}

_P = 2 ** 255 - 19
_L = 2 ** 252 + 27742317777372353535851937790883648493
_D = -121665 * pow(121666, _P - 2, _P) % _P
_I = pow(2, (_P - 1) // 4, _P)


def _inv(x):
    return pow(x, _P - 2, _P)


def _add(p, q):
    (x1, y1, z1, t1), (x2, y2, z2, t2) = p, q
    a, b = (y1 - x1) * (y2 - x2) % _P, (y1 + x1) * (y2 + x2) % _P
    c, d = 2 * t1 * t2 * _D % _P, 2 * z1 * z2 % _P
    e, f, g, h = b - a, d - c, d + c, b + a
    return e * f % _P, g * h % _P, f * g % _P, e * h % _P


def _base():
    y = 4 * _inv(5) % _P
    x2 = (y * y - 1) * _inv(_D * y * y + 1) % _P
    x = pow(x2, (_P + 3) // 8, _P)
    if (x * x - x2) % _P:
        x = x * _I % _P
    if x & 1:
        x = _P - x
    return x, y, 1, x * y % _P


def _mul(s, p):
    q = (0, 1, 1, 0)
    while s:
        if s & 1:
            q = _add(q, p)
        p = _add(p, p)
        s >>= 1
    return q


def public_key(seed32):
    """The 32-byte ed25519 public key for a 32-byte seed (RFC 8032 5.1.5)."""
    h = bytearray(hashlib.sha512(seed32).digest()[:32])
    h[0] &= 248
    h[31] = (h[31] & 63) | 64
    x, y, z, _ = _mul(int.from_bytes(h, "little"), _base())
    zi = _inv(z)
    x, y = x * zi % _P, y * zi % _P
    return (y | ((x & 1) << 255)).to_bytes(32, "little")


def node_name(role, branch, pod):
    return f"{role}-{branch}-{pod:02d}"


def mgmt_ip(pod, branch, role):
    return f"{MGMT_NET_BASE}{pod + 1}.{NODE_HOST_BASE + BRANCH_SLOT[branch] + ROLE_SLOT[role]}"


def host_seed(class_seed, name):
    return hmac.new(class_seed.encode(), f"netlab-hostkey:{name}".encode(), hashlib.sha256).digest()


def _s(b):
    return struct.pack(">I", len(b)) + b


def public_blob(seed32):
    return _s(b"ssh-ed25519") + _s(public_key(seed32))


def public_line(seed32):
    """'ssh-ed25519 AAAA...' (authorized_keys / known_hosts form)."""
    return "ssh-ed25519 " + base64.b64encode(public_blob(seed32)).decode()


def private_pem(seed32):
    """An unencrypted OpenSSH-format private key file (what sshd's HostKey reads)."""
    pub = public_key(seed32)
    body = _s(b"ssh-ed25519") + _s(pub) + _s(seed32 + pub) + _s(b"")
    body = struct.pack(">II", 0x1A2B3C4D, 0x1A2B3C4D) + body
    body += bytes(range(1, 8 - len(body) % 8 + 1)) if len(body) % 8 else b""
    blob = b"openssh-key-v1\0" + _s(b"none") + _s(b"none") + _s(b"") + struct.pack(">I", 1) + _s(public_blob(seed32)) + _s(body)
    b64 = base64.b64encode(blob).decode()
    lines = [b64[i:i + 70] for i in range(0, len(b64), 70)]
    return "-----BEGIN OPENSSH PRIVATE KEY-----\n" + "\n".join(lines) + "\n-----END OPENSSH PRIVATE KEY-----\n"


def known_hosts(class_seed, pods):
    """known_hosts text for every node of pods 0..PODS-1 (name and management address). A superset of the nodes a
    run actually has (the switch and branch M are optional); an entry for a node that is not there does no harm."""
    out = []
    for pod in range(pods):
        for b in BRANCH_SLOT:
            for role in ROLE_SLOT:
                name = node_name(role, b, pod)
                out.append(f"{name},{mgmt_ip(pod, b, role)} {public_line(host_seed(class_seed, name))}")
    return "\n".join(out) + "\n"


def pods_from_env(env):
    """Pod count: the facilitator's pod 00, STUDENT_COUNT students and BOT_COUNT demo bots."""
    return 1 + int(env.get("STUDENT_COUNT") or 30) + int(env.get("BOT_COUNT") or 0)


if __name__ == "__main__":
    import os
    import sys
    if not os.environ.get("STUDENT_PASSWORD_SEED"):
        sys.exit("netlab hostkeys: STUDENT_PASSWORD_SEED is empty")
    sys.stdout.write(known_hosts(os.environ["STUDENT_PASSWORD_SEED"], pods_from_env(os.environ)))
