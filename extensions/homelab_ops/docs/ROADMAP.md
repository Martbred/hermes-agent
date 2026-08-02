# Homelab Operations Platform Roadmap

## 1. Operations Engine

**Implemented foundation:** inventory-bound host actions, fixed command templates, SSH runner, reboot verification, service/container allowlists.

Next:
- Proxmox VM/LXC lifecycle adapters
- Home Assistant service adapter
- backup and snapshot actions
- maintenance-window awareness
- idempotency keys and action cancellation

## 2. Monitoring Engine

Adapters and normalized health schema for:
- Zabbix
- Prometheus
- Docker
- Proxmox
- Home Assistant
- Pi-hole
- Suricata
- UPS
- Palo Alto
- Cloudflare and Tailscale

All adapters will emit a common `Observation` model with source, target, metric/event, severity, timestamps and evidence.

## 3. Security Engine

- normalize Suricata, Fail2Ban, Cloudflare, GitHub and identity events
- correlate events by host, account, IP and time window
- maintain known-device inventory
- produce evidence-backed risk assessments
- require explicit approval before containment actions

## 4. AI Decision Engine

- deterministic rules before LLM recommendations
- recommendations include evidence, confidence, blast radius and rollback
- no direct AI-to-shell path
- simulation/dry-run for multi-step plans
- policy prevents autonomous high-risk operations

## 5. Automation Engine

- event-condition-action workflows
- cooldowns, deduplication and rate limits
- maintenance windows
- retries with bounded backoff
- rollback and compensation steps
- notification routing

## 6. Homelab Inventory / Knowledge Graph

- hosts, services, containers, VMs, network devices and dependencies
- ownership, location, lifecycle and backup metadata
- relationships such as `runs_on`, `depends_on`, `monitored_by` and `protected_by`
- discovery must propose changes; it must not silently overwrite authoritative inventory

## 7. Skill System

Planned skills:
- linux-operations
- docker-operations
- zabbix-operations
- proxmox-operations
- home-assistant-operations
- network-investigation
- backup-and-restore
- incident-response

Each skill invokes typed operations tools rather than arbitrary terminal commands.

## 8. Approval Engine

**Implemented foundation:** short-lived HMAC tokens bound to exact plan, actor, target and parameters.

Next:
- role-based authorization
- two-person approval for critical actions
- approval via Telegram/Discord/dashboard
- break-glass workflow
- replay protection persisted in a database

## 9. Audit Log

**Implemented foundation:** append-only JSONL lifecycle events.

Next:
- SQLite/PostgreSQL event store
- hash chaining for tamper evidence
- correlation IDs across plans and sub-actions
- searchable UI and retention policy
- export to Loki/SIEM

## 10. Dashboard and API

- REST and MCP façade over the operations core
- live health overview
- approvals inbox
- incident timeline
- inventory editor with validation
- automation builder
- audit explorer
- least-privilege API tokens

## Delivery sequence

1. Harden and deploy current vertical slice.
2. Add native Hermes tool adapter and REST/MCP API.
3. Add Zabbix, Docker and Proxmox read-only adapters.
4. Add dashboard status and approval inbox.
5. Add security correlation and known-device inventory.
6. Add automations with dry-run and rollback.
7. Add decision support and dependency-aware planning.
8. Add controlled autonomous remediation for low-risk actions only.
