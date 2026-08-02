# Architecture

```text
Hermes conversation / scheduler / dashboard
                 |
                 v
        Homelab Operations Skill
                 |
                 v
          Operations Engine
       /         |          \
Inventory   Approval      Audit
                 |
                 v
       Typed action registry
                 |
                 v
             SSH runner
                 |
                 v
       Managed homelab hosts
```

## Trust boundaries

- The language model is treated as an untrusted planner.
- The operations engine is the policy-enforcement point.
- Inventory defines valid targets and per-target resources.
- The action registry defines every executable command.
- Approval tokens authorize one exact, short-lived action plan.
- SSH credentials remain on the Hermes execution host.
- Managed hosts enforce a second control with restricted sudoers rules.

## Data flow for reboot

1. Hermes resolves the requested host name.
2. The engine rejects missing or disabled hosts.
3. The engine creates an immutable plan and logs it.
4. The signer issues a token bound to plan ID, actor, target, action and parameters.
5. After user approval, the engine verifies the token.
6. The fixed `sudo -n systemctl reboot` action is sent over SSH.
7. The runner confirms the host becomes unavailable.
8. The runner waits for SSH recovery.
9. The result and verification evidence are appended to the audit log.

## Extension points

Monitoring, security, automation and dashboard components should depend on the operations engine's typed models rather than importing SSH implementation details. New actions require:

- an action definition
- parameter validation
- a fixed command factory or native adapter
- a risk classification
- verification behavior
- tests

Arbitrary command execution is intentionally not an extension point.
