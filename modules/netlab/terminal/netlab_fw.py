#!/usr/bin/env python3
"""netlab per-uid firewall for the shared terminal (run by start.d/50-netlab.sh as root).

All students share this container's network namespace, and this container has an interface on every pod's management
network (netlab_mgmt_NN), so without this
student N's shell could open TCP to pod M's nodes. The rules go on the OUTPUT chain, matched by the sending uid:

  uid 0                      -> RETURN (the facilitator and the container's own services)
  uid of pod N's account     -> RETURN for pod N's management block only
  anyone else, to any pod network -> DROP (the connection never opens; the sender sees a timeout)

The INPUT side (NETLAB_INPUT): a student is root on their own nodes, and web-terminal sits on its pod's network too, so
without it a node could open web-terminal's control port (7682) and the rest. On each pod-network interface it
accepts only replies to what this container opened (established/related) and drops new inbound connections.

Traffic to anywhere else (the gateway, DNS, Forgejo, the checker on workshop_lab) never matches `-d MGMT_CIDR`.
build_rules() is pure (tests: modules/netlab/test_fw.py); main() resolves uids and loads the result with
iptables-restore --noflush, which replaces the chain in one step (no open window on a re-run).
Pod addressing must match generate.py (mgmt_ip); test_fw.py checks the two agree.
"""
import os
import pwd
import subprocess
import sys

CHAIN = "NETLAB_ISOLATION"
MGMT_CIDR = "10.80.0.0/16"          # generate.py MGMT_CIDR: every pod's management network lies inside it
MGMT_NET_BASE = (10, 80)            # generate.py MGMT_NET_BASE


def pod_block(pod):
    """CIDR of pod N's management network (generate.py mgmt_cidr)."""
    if not 0 <= pod < 32:
        raise ValueError(f"pod {pod} is outside the management layout")
    a, b = MGMT_NET_BASE
    return f"{a}.{b}.{pod + 1}.0/24"


def roster(env):
    """[(username, pod)]: studentNN is pod NN, demo bot testuserK is pod STUDENT_COUNT+K (account.d/57-netlab.sh)."""
    students = int(env.get("STUDENT_COUNT") or 30)
    bots = int(env.get("BOT_COUNT") or 0)
    prefix = env.get("STUDENT_PREFIX") or "student"
    bprefix = env.get("BOT_PREFIX") or "testuser"
    out = [(f"{prefix}{n:02d}", n) for n in range(1, students + 1)]
    return out + [(f"{bprefix}{k}", students + k) for k in range(1, bots + 1)]


def build_rules(uid_pods, mgmt=MGMT_CIDR, chain=CHAIN):
    """iptables-restore text for the filter table. uid_pods: {uid: pod}. Uid 0 is always left alone."""
    lines = ["*filter", f":{chain} - [0:0]", f"-A {chain} -m owner --uid-owner 0 -j RETURN"]
    for uid, pod in sorted(uid_pods.items()):
        if uid != 0:
            lines.append(f"-A {chain} -d {pod_block(pod)} -m owner --uid-owner {uid} -j RETURN")
    # DROP, not REJECT: measured here (iptables-nft in the rootless netns), REJECT in OUTPUT never reaches the local
    # socket in any of its variants (tcp-reset, icmp-port-unreachable, ...), so it behaves like DROP and needs a module.
    lines += [f"-A {chain} -d {mgmt} -j DROP", "COMMIT", ""]
    return "\n".join(lines)


IN_CHAIN = "NETLAB_INPUT"


def build_input_rules(ifaces, chain=IN_CHAIN):
    """iptables-restore text: on each of IFACES (the pod networks' interfaces) accept replies, drop everything new."""
    lines = ["*filter", f":{chain} - [0:0]"]
    for iface in ifaces:
        lines += [f"-A {chain} -i {iface} -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT",
                  f"-A {chain} -i {iface} -j DROP"]
    return "\n".join(lines + ["COMMIT", ""])


def mgmt_ifaces(mgmt=MGMT_CIDR):
    """Names of this container's interfaces whose IPv4 address lies in MGMT (one per pod network)."""
    import fcntl
    import ipaddress
    import socket
    import struct
    net = ipaddress.ip_network(mgmt)
    found = []
    # The terminal image has no `ip`; ask the kernel (SIOCGIFADDR) for each interface's IPv4 address.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        for ifname in sorted(os.listdir("/sys/class/net")):
            try:
                packed = fcntl.ioctl(s.fileno(), 0x8915, struct.pack("256s", ifname.encode()[:15]))
            except OSError:
                continue
            if ipaddress.ip_address(socket.inet_ntoa(packed[20:24])) in net:
                found.append(ifname)
    return found


def apply_input():
    """Load NETLAB_INPUT, jump to it first in INPUT, read it back. 0 on success."""
    ifaces = mgmt_ifaces()
    if not ifaces:
        print("netlab firewall: no interface on a pod management network; cannot protect web-terminal's own ports", file=sys.stderr)
        return 1
    r = run(["iptables-restore", "--noflush"], input=build_input_rules(ifaces))
    if r.returncode != 0:
        print(f"netlab firewall: iptables-restore (input) failed: {r.stderr.strip()}", file=sys.stderr)
        return 1
    if run(["iptables", "-C", "INPUT", "-j", IN_CHAIN]).returncode != 0:
        r = run(["iptables", "-I", "INPUT", "1", "-j", IN_CHAIN])
        if r.returncode != 0:
            print(f"netlab firewall: cannot jump to {IN_CHAIN}: {r.stderr.strip()}", file=sys.stderr)
            return 1
    shown = run(["iptables", "-S", IN_CHAIN]).stdout
    if (shown.count("-j ACCEPT") != len(ifaces) or shown.count("-j DROP") != len(ifaces)
            or any(f"-i {i} " not in shown for i in ifaces)):
        print(f"netlab firewall: {IN_CHAIN} does not hold the rules just written:\n{shown}", file=sys.stderr)
        return 1
    print(f"netlab firewall: new inbound connections on {len(ifaces)} pod network interface(s) dropped", file=sys.stderr)
    return 0


def run(cmd, **kw):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, **kw)
    except OSError as e:            # no iptables binary at all
        return subprocess.CompletedProcess(cmd, 127, "", str(e))


def main(env=os.environ):
    uid_pods = {}
    for name, pod in roster(env):
        try:
            uid_pods[pwd.getpwnam(name).pw_uid] = pod
        except KeyError:
            # No account, nobody to allow; the catch-all DROP still covers the uid if it ever appears.
            print(f"netlab firewall: no account {name}; pod {pod:02d} has no one allowed", file=sys.stderr)
    rules = build_rules(uid_pods)
    r = run(["iptables-restore", "--noflush"], input=rules)
    if r.returncode != 0:
        print(f"netlab firewall: iptables-restore failed: {r.stderr.strip()}", file=sys.stderr)
        return 1
    if run(["iptables", "-C", "OUTPUT", "-j", CHAIN]).returncode != 0:
        # First in OUTPUT, so another chain's early ACCEPT cannot let a student past it.
        r = run(["iptables", "-I", "OUTPUT", "1", "-j", CHAIN])
        if r.returncode != 0:
            print(f"netlab firewall: cannot jump to {CHAIN}: {r.stderr.strip()}", file=sys.stderr)
            return 1
    # Read it back: the hook only reports success if the kernel really holds one RETURN per account, and the catch-all DROP.
    shown = run(["iptables", "-S", CHAIN]).stdout
    want = len(uid_pods) + 1
    if shown.count("-j RETURN") != want or shown.count("-j DROP") != 1:
        print(f"netlab firewall: {CHAIN} does not hold the rules just written:\n{shown}", file=sys.stderr)
        return 1
    print(f"netlab firewall: {len(uid_pods)} account(s) limited to their own pod network", file=sys.stderr)
    return apply_input()


if __name__ == "__main__":
    sys.exit(main())
