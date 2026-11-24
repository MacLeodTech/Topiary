#!/usr/bin/env python3
"""Header rules and the keepalive rule for engine/gateway/Caddyfile (P13, E1).

Every reverse_proxy block that does not go to a public upstream must send
X-Gateway-Token, and X-Auth-User may only be set from the allocator's
X-Session-User or X-Dojo-User, never passed through from the client.
Public upstreams (no identity) are allowlisted by name and must not carry
the token or an identity header.
"""
import re
import sys

PATH = "engine/gateway/Caddyfile"
PUBLIC = {"presentation:8080", "git-server:3000"}
# Upstream whose identity is a dynamic port picked by the allocator's check.
TOKENLESS_OK = {"web-terminal-ingress"}  # ingress checks the allocator's cookie auth itself

text = open(PATH).read().splitlines()
errors = []
i = 0
while i < len(text):
    m = re.match(r"\s*reverse_proxy\s+(\S+)(\s*\{)?\s*$", text[i])
    if not m:
        i += 1
        continue
    start, upstream, block = i + 1, m.group(1), []
    if m.group(2):
        depth = 1
        i += 1
        while i < len(text) and depth:
            depth += text[i].count("{") - text[i].count("}")
            block.append(text[i])
            i += 1
    else:
        i += 1
    body = "\n".join(block)
    host = upstream.split(":")[0]
    if upstream in PUBLIC:
        if re.search(r"header_up\s+X-Gateway-Token\s+\S", body):
            errors.append(f"{PATH}:{start}: public upstream {upstream} gets the gateway token")
        continue
    if host in TOKENLESS_OK:
        continue
    if not re.search(r"header_up\s+X-Gateway-Token\s+\S", body):
        errors.append(f"{PATH}:{start}: reverse_proxy {upstream} has no header_up X-Gateway-Token")
    for v in re.findall(r"header_up\s+X-Auth-User\s+(\S+)", body):
        if not re.search(r"X-(Session|Dojo)-User", v):
            errors.append(f"{PATH}:{start}: X-Auth-User set from {v}, not X-Session-User/X-Dojo-User")
# E1: Caddy must drop an idle upstream connection before the allocator does,
# or it can send a request down one the allocator is closing (a 502).
ALLOCATOR = "engine/allocator/handler.py"
m_idle = re.search(r"^\s*IDLE_TIMEOUT\s*=\s*(\d+)", open(ALLOCATOR).read(), re.M)
keepalives = [(n, int(v), u) for n, line in enumerate(text, 1)
              for v, u in re.findall(r"^\s*keepalive\s+(\d+)(s|m)\b", line)]
if not m_idle:
    errors.append(f"{ALLOCATOR}: IDLE_TIMEOUT not found")
for n, v, u in keepalives:
    seconds = v * (60 if u == "m" else 1)
    if m_idle and seconds >= int(m_idle.group(1)):
        errors.append(f"{PATH}:{n}: keepalive {v}{u} must stay below the allocator's IDLE_TIMEOUT "
                      f"({m_idle.group(1)} s)")
if m_idle and not keepalives:
    errors.append(f"{PATH}: no keepalive found for the allocator transport")
print("\n".join(errors) if errors else f"{PATH}: header rules OK")
sys.exit(1 if errors else 0)
