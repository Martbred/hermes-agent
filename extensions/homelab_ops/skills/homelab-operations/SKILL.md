---
name: homelab-operations
description: Safely inspect and operate Martin's homelab through the allowlisted Hermes operations engine.
---

# Homelab Operations

Use this skill when the user asks to inspect, restart, update or otherwise operate an inventory-managed homelab host, service or container.

## Safety rules

1. Never execute arbitrary shell supplied by the user.
2. Resolve the target through `config/inventory.json`.
3. Use only actions returned by `python -m homelab_ops.cli actions`.
4. Create a plan before any state-changing action.
5. Present target, impact, risk and affected role/services before requesting approval.
6. Never reuse an approval token for another plan.
7. After execution, report both command result and verification result.
8. Do not hide failed verification even when the remote command returned success.

## Read-only workflow

```bash
python -m homelab_ops.cli plan host.status HOST --actor martin --save-plan /tmp/hermes-plan.json
python -m homelab_ops.cli execute --plan-file /tmp/hermes-plan.json
```

## Reboot workflow

Create a plan:

```bash
python -m homelab_ops.cli plan host.reboot HOST --actor martin --save-plan /tmp/hermes-plan.json
```

Show the user the resulting risk and impact. After explicit approval, execute with the exact token returned by the planning command:

```bash
python -m homelab_ops.cli execute --plan-file /tmp/hermes-plan.json --approval-token TOKEN
```

A successful reboot is not complete until SSH disappears and returns. Report `recovery_verified` explicitly.

## Service and container workflow

Use only names declared in the host inventory:

```bash
python -m homelab_ops.cli plan service.restart HOST --actor martin --parameter service=zabbix-agent2 --save-plan /tmp/hermes-plan.json
python -m homelab_ops.cli plan docker.restart HOST --actor martin --parameter container=grafana --save-plan /tmp/hermes-plan.json
```
