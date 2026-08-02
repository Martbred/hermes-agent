# Deployment

## 1. Install the extension

```bash
cd extensions/homelab_ops
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
pytest
```

## 2. Create a dedicated SSH key

Run this on the Hermes host:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/hermes_homelab_ed25519 -C hermes-homelab-ops
```

Install the public key only on inventory-managed hosts.

## 3. Configure restricted sudo

For Linux reboot and service restart, create `/etc/sudoers.d/hermes-ops` on each managed host. Replace `martbred` and the allowlisted services as needed:

```sudoers
martbred ALL=(root) NOPASSWD: /usr/bin/systemctl reboot
martbred ALL=(root) NOPASSWD: /usr/bin/systemctl restart pihole-FTL
martbred ALL=(root) NOPASSWD: /usr/bin/systemctl restart suricata
martbred ALL=(root) NOPASSWD: /usr/bin/systemctl restart zabbix-agent2
```

Validate with:

```bash
sudo visudo -cf /etc/sudoers.d/hermes-ops
```

Do not grant unrestricted `sudo`, a shell, or wildcard command arguments.

## 4. Pin host keys

Connect once manually from the Hermes host:

```bash
ssh -i ~/.ssh/hermes_homelab_ed25519 martbred@192.168.68.58 true
```

Confirm the fingerprint out of band. Production inventory should keep `verify_host_key` set to `true`.

## 5. Configure inventory and secret

```bash
cp config/inventory.example.json config/inventory.json
chmod 600 config/inventory.json
export HERMES_OPS_APPROVAL_SECRET="$(openssl rand -hex 32)"
```

Store the secret in the Hermes service environment or a secrets manager, not in Git.

## 6. Install the Hermes skill

Copy or symlink:

```bash
ln -s "$PWD/skills/homelab-operations" ~/.hermes/skills/homelab-operations
```

Restart the Hermes gateway if it does not reload skills dynamically.

## 7. Smoke test without changing state

```bash
python -m homelab_ops.cli inventory
python -m homelab_ops.cli actions
python -m homelab_ops.cli plan host.status raspberrypi-5 --actor martin --save-plan /tmp/status-plan.json
python -m homelab_ops.cli execute --plan-file /tmp/status-plan.json
```

## 8. Reboot test

Perform this only during a suitable maintenance window:

```bash
python -m homelab_ops.cli plan host.reboot raspberrypi-5 --actor martin --save-plan /tmp/reboot-plan.json
```

Review the returned plan and token, then execute using the exact token. A successful result must include `recovery_verified: true`.
