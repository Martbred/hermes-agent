# Hermes Homelab Operations Platform

A security-focused operations extension for Hermes Agent. This module implements the first vertical slice of the planned platform:

1. host inventory
2. operations engine
3. approval engine
4. SSH execution
5. post-action verification
6. append-only audit log
7. skill interface for Hermes

The implementation deliberately does **not** expose arbitrary shell execution. Every action is registered in a strict allowlist and validated before execution.

## Current actions

- `host.status` — read-only SSH health check
- `host.reboot` — controlled Linux reboot with approval and recovery verification
- `service.restart` — restart an allowlisted systemd service
- `docker.restart` — restart an allowlisted Docker container
- `system.updates_check` — report pending Debian/Ubuntu updates

## Quick start

```bash
cd extensions/homelab_ops
cp config/inventory.example.json config/inventory.json
cp config/policy.example.json config/policy.json
python -m homelab_ops.cli inventory
python -m homelab_ops.cli plan host.reboot raspberrypi-5 --actor martin
```

The `plan` command returns a signed approval token for actions requiring confirmation. Execute it with:

```bash
python -m homelab_ops.cli execute host.reboot raspberrypi-5 \
  --actor martin \
  --approval-token '<token>'
```

Set the signing secret before using approval tokens:

```bash
export HERMES_OPS_APPROVAL_SECRET='replace-with-a-long-random-secret'
```

## Security model

- Inventory is authoritative: unknown hosts are rejected.
- Actions are explicit and allowlisted.
- Service and container names must be declared per host.
- High-risk actions require a short-lived HMAC-signed approval token.
- SSH uses batch mode and strict host-key checking by default.
- Commands are fixed templates, never user-provided shell strings.
- Every plan, approval, execution and verification result is written to JSONL audit storage.
- Reboot verification waits for the host to disappear and return over SSH.

## Integration direction

This extension is intentionally isolated from upstream Hermes internals. Hermes can invoke the CLI from a skill today; a native tool adapter and REST/MCP façade can be added without changing the operations core.

See `docs/ROADMAP.md` for the implementation plan covering monitoring, security analytics, decision support, automation, inventory, skills, approvals, audit and dashboard capabilities.
