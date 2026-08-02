# Security Controls

## Implemented

- no arbitrary shell action
- authoritative host inventory
- per-host service and container allowlists
- short-lived HMAC approvals bound to exact plans
- SSH batch mode
- strict host-key checking by default
- fixed command templates
- bounded output capture
- append-only lifecycle audit events
- reboot disappearance and recovery verification
- runtime inventory, policy, secrets and audit data excluded from Git

## Deployment requirements

- dedicated SSH key for Hermes
- restricted sudoers entries with exact binaries and arguments
- host key fingerprints verified out of band
- approval secret stored in service environment or secrets manager
- Hermes endpoint protected by strong authentication and network controls
- logs forwarded to protected storage

## Known limitations in v0.1

- approval replay prevention is limited to token expiry; persistent nonce consumption is planned
- JSONL audit logs are append-only by convention but not yet hash-chained
- RBAC and two-person approvals are not implemented
- policy example is documented but not yet enforced by a dedicated policy engine
- no API authentication layer exists because v0.1 is CLI/skill based
