#!/bin/sh
# ctf-range start.d hook: trim the student `dojo` command list to what a CTF pack has.
#
# - `dojo challenge` -- the achievements module (appended last in the image chain, so its
#   link would win at build time) links `challenge` to its lab-challenge client. A CTF pack
#   has no challenges: the pack is the challenge. Whatever follows `dojo challenge`, say so.
# - `dojo reset` -- the checker only resets the ctf-defend targets (CTF_DEFEND_TARGETS), so
#   in every other pack the command could never succeed; remove it there.
set -eu
cmd_d=/usr/local/share/dojo/cmd.d
mkdir -p "$cmd_d"
# rm first: `challenge` is a symlink to the real dojo-check, and writing through it would replace that.
rm -f "$cmd_d/challenge"
cat > "$cmd_d/challenge" <<'SCRIPT'
#!/bin/sh
# dojo-summary: (no challenges here: the CTF pack is the challenge)
echo "There are no challenges in the CTF packs. The CTF pack is the challenge"
SCRIPT
chmod 0755 "$cmd_d/challenge"
if [ -z "${CTF_DEFEND_TARGETS:-}" ]; then
  rm -f "$cmd_d/reset"
fi
