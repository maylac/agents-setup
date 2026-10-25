---
name: vantik-prod-verify
description: Read-only checks against the Vantik production container on the NAS - pull a consistent SQLite snapshot for local analysis (online backup, quick_check, foreign keys, counts) and confirm that a pushed master commit has actually landed (CI → Publish → Watchtower → /health revision). Use before any analysis of real learning history, before writes to the live DB, and after every reskilling-os push. Trigger phrases include 「本番DBを見て」「本番反映を確認」「デプロイ届いた？」「誤答履歴を集計して」.
---

# Vantik production verify (read-only)

Two things every Vantik task repeats: get a trustworthy copy of the live SQLite
database without touching it, and prove that a deploy landed. Both are scripted here.
Nothing in this skill writes to production except the optional retained backup.

## Connect

- `ssh ugnas` is the alias for the NAS. Its mDNS host only resolves on the home LAN;
  off-LAN it fails with "No route to host". Then use the tailnet name recorded in
  auto-memory (`nas-remote-access`) with `-o HostKeyAlias=<original host>` and start
  Tailscale on the Mac if needed. Never write hostnames or addresses into this skill.
- Container `vantik`, DB `/app/data/vantik.db`, retained backups `/app/backups`.
  `scp` to the NAS fails; everything goes through `ssh … 'docker exec -i …'` stdin/stdout.
- Set `VANTIK_SSH` / `VANTIK_CONTAINER` if the alias or container name differs.

## 1. Snapshot for analysis

```bash
bash ~/.agents/skills/vantik-prod-verify/scripts/snapshot.sh            # → /tmp/vantik-snapshot-<ts>.db + JSON summary
bash ~/.agents/skills/vantik-prod-verify/scripts/snapshot.sh --out ~/tasks/<task>/snapshot.db --integrity <reskilling-os>/scripts/vantik_integrity_check.py
bash ~/.agents/skills/vantik-prod-verify/scripts/snapshot.sh --keep     # also leaves a dated copy in /app/backups (use before a live write)
```

- Default mode runs `sqlite3.Connection.backup()` inside the container from a
  `mode=ro` connection into a container temp file, streams it out, deletes the temp
  file. WAL content is included; a plain `cp` of `vantik.db` is not a valid copy.
- The script prints `quick_check`, `foreign_key_violations`, `journal_mode` and row
  counts for questions / attempts / study_sessions and exits non-zero if the copy is
  not `ok`. Report those numbers; they are the provenance of every later figure.
- Never open the live DB over SMB. Never analyse `vantik.db-wal` separately.
- Analysis joins go through stable IDs (`attempt_id → question_version_id → question_id`),
  not question numbers. "Latest result per question" means latest attempt per
  `question_id`, not per version.
- `--keep` uses the app's own `vantik backup` CLI (output `vantik-<timestamp>.db` in
  `/app/backups`). Use it right before any write to production and record the path.

## 2. Deploy landed?

```bash
bash ~/.agents/skills/vantik-prod-verify/scripts/deploy_check.sh --repo <reskilling-os checkout>          # expected = origin/master
bash ~/.agents/skills/vantik-prod-verify/scripts/deploy_check.sh --expect <sha> --wait 20                 # poll up to 20 min
```

Pipeline (see the repo's `README.deploy.md`): push to `master` → workflow **CI** →
workflow **Publish** (only on CI success, pushes `ghcr.io/…:latest` and `:sha-<7>`) →
Watchtower polls (default 120 s) → container restarts → `/health` returns
`{"status":"ok","revision":"<full sha>"}`. The script shows the last CI/Publish runs,
the live revision, the image label `org.opencontainers.image.revision`, and whether
they match the expected SHA.

Interpretation:

- `CI failure` + `Publish skipped` → nothing was deployed; the live revision is the
  previous commit. Say so explicitly instead of "deploy pending".
- Revision matches but behaviour does not → check the API with
  `docker exec vantik curl -s http://localhost:8000/api/...` from inside the
  container (the host-side bind is on the tailnet address, not localhost).
- Report revision, container `Status` (`healthy`), and the measured API values
  separately from DB integrity; do not mix the three.

## Rules

- Read-only by default. Writes to production (DB rows, `review-videos.json`,
  compose, Watchtower, Tailscale) are outside this skill and need their own approval.
- Do not restart `vantik`, `watchtower`, `vantik-runner` or the remote-control hosts.
- Keep the Japanese report short: snapshot path + integrity line, counts, live
  revision vs expected, and the CI/Publish verdict.
