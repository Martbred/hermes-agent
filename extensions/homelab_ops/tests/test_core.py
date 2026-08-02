import json
from pathlib import Path

import pytest

from homelab_ops.core import (
    ActionPlan,
    ApprovalError,
    ApprovalSigner,
    AuditLog,
    Host,
    Inventory,
    OperationsEngine,
    ValidationError,
)


class FakeRunner:
    def __init__(self):
        self.calls = []

    def run(self, host, remote_argv, timeout=None):
        self.calls.append((host.name, remote_argv))

        class Result:
            returncode = 0
            stdout = "ok"
            stderr = ""

        return Result()

    def verify_reboot(self, host):
        return True


def inventory(tmp_path: Path) -> Inventory:
    path = tmp_path / "inventory.json"
    path.write_text(
        json.dumps(
            {
                "hosts": [
                    {
                        "name": "rpi-5",
                        "address": "192.168.68.58",
                        "user": "martin",
                        "services": ["suricata"],
                        "containers": ["grafana"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return Inventory.load(path)


def test_unknown_host_is_rejected(tmp_path):
    inv = inventory(tmp_path)
    with pytest.raises(ValidationError):
        inv.get("missing")


def test_non_allowlisted_service_is_rejected(tmp_path):
    engine = OperationsEngine(
        inventory(tmp_path),
        AuditLog(tmp_path / "audit.jsonl"),
        ApprovalSigner("x" * 32),
        FakeRunner(),
    )
    with pytest.raises(ValidationError):
        engine.plan("service.restart", "rpi-5", "martin", {"service": "sshd"})


def test_approval_token_is_bound_to_plan(tmp_path):
    engine = OperationsEngine(
        inventory(tmp_path),
        AuditLog(tmp_path / "audit.jsonl"),
        ApprovalSigner("x" * 32),
        FakeRunner(),
    )
    plan, token = engine.plan("host.reboot", "rpi-5", "martin")
    altered = ActionPlan(**{**plan.__dict__, "target": "another-host"})
    with pytest.raises(ApprovalError):
        engine.signer.verify(token, altered)


def test_reboot_executes_fixed_command_and_verifies_recovery(tmp_path):
    runner = FakeRunner()
    engine = OperationsEngine(
        inventory(tmp_path),
        AuditLog(tmp_path / "audit.jsonl"),
        ApprovalSigner("x" * 32),
        runner,
    )
    plan, token = engine.plan("host.reboot", "rpi-5", "martin")
    result = engine.execute(plan, token)
    assert runner.calls == [("rpi-5", ["sudo", "-n", "systemctl", "reboot"])]
    assert result.status == "completed"
    assert result.recovery_verified is True


def test_audit_log_contains_lifecycle_events(tmp_path):
    runner = FakeRunner()
    path = tmp_path / "audit.jsonl"
    engine = OperationsEngine(
        inventory(tmp_path),
        AuditLog(path),
        ApprovalSigner("x" * 32),
        runner,
    )
    plan, token = engine.plan("host.reboot", "rpi-5", "martin")
    engine.execute(plan, token)
    events = [json.loads(line)["event"] for line in path.read_text().splitlines()]
    assert events == ["action.planned", "action.approved", "action.started", "action.completed"]
