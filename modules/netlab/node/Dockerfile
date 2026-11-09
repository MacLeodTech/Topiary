# One image for every netlab node; NODE_ROLE (pc, sw, fw, web) picks the job (entrypoint.sh).
# Root over SSH with a per-pod password: no-new-privileges breaks sudo, so there is no sudo here.
FROM docker.io/library/alpine:3.24@sha256:294b683cb724975bec92580e1e685676bd4b50bda910ddb8c51d4cabeaec77e6
RUN apk add --no-cache openssh python3 iptables iproute2 nginx curl openssl busybox-extras \
    && rm -f /etc/nginx/http.d/default.conf
COPY entrypoint.sh /usr/local/bin/netlab-entrypoint
RUN chmod 0755 /usr/local/bin/netlab-entrypoint
# 30 s, not 10: a 15-pod class has 120 nodes, and each check is a podman exec (about 12 a second at 10 s).
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD nc -z 127.0.0.1 22 || exit 1
ENTRYPOINT ["/usr/local/bin/netlab-entrypoint"]
