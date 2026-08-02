from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


class OpsError(RuntimeError):
    """Base error for the operations platform."""


class ValidationError(OpsError):
    pass


class ApprovalError(OpsError):
    pass


class ExecutionError(OpsError):
    pass


@dataclass(frozen=True)
class Host:
    name: str
    address: str
    user: str
    port: int = 22
    roles: tuple[str, ...] = ()
    services: tuple[str, ...] = ()
    containers: tuple[str, ...] = ()
    enabled: bool = True
    ssh_identity_file: str | None = None
    verify_host_key: bool = True


@dataclass(frozen=True)
class ActionDefinition:
    name: str
    risk: str
    requires_approval: bool
    description: str
    command_factory: Callable[[Host, dict[str, Any]], list[str]]
    validator: Callable[[Host, dict[str, Any]], None] | None = None
    verify_recovery: bool = False


@dataclass
class ActionPlan:
    plan_id: str
    action: str
    target: str
    actor: str
    risk: str
    requires_approval: bool
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at_epoch: int = 0


@dataclass
class ActionResult:
    plan_id: str
    action: str
    target: str
    status: str
    started_at: str
    completed_at: str
    exit_code: int | None
    stdout: str
    stderr: str
    recovery_verified: bool | None = None


class Inventory:
    def __init__(self, hosts: dict[str, Host]):
        self._hosts = hosts

    @classmethod
    def load(cls, path: str | Path) -> "Inventory":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        hosts: dict[str, Host] = {}
        for item in raw.get("hosts", []):
            host = Host(
                name=item["name"],
                address=item["address"],
                user=item["user"],
                port=int(item.get("port", 22)),
                roles=tuple(item.get("roles", [])),
                services=tuple(item.get("services", [])),
                containers=tuple(item.get("containers", [])),
                enabled=bool(item.get("enabled", True)),
                ssh_identity_file=item.get("ssh_identity_file"),
                verify_host_key=bool(item.get("verify_host_key", True)),
            )
            if host.name in hosts:
                raise ValidationError(f"Duplicate host name: {host.name}")
            hosts[host.name] = host
        return cls(hosts)

    def get(self, name: str) -> Host:
        host = self._hosts.get(name)
        if host is None:
            raise ValidationError(f"Unknown host: {name}")
        if not host.enabled:
            raise ValidationError(f"Host is disabled: {name}")
        return host

    def list(self) -> list[Host]:
        return sorted(self._hosts.values(), key=lambda host: host.name)


class AuditLog:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event: str, payload: dict[str, Any]) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **payload,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


class ApprovalSigner:
    def __init__(self, secret: str, ttl_seconds: int = 300):
        if len(secret) < 32:
            raise ValidationError("Approval secret must be at least 32 characters")
        self.secret = secret.encode("utf-8")
        self.ttl_seconds = ttl_seconds

    def issue(self, plan: ActionPlan) -> str:
        payload = {
            "plan_id": plan.plan_id,
            "action": plan.action,
            "target": plan.target,
            "actor": plan.actor,
            "parameters": plan.parameters,
            "expires": int(time.time()) + self.ttl_seconds,
            "nonce": secrets.token_hex(8),
        }
        encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        signature = hmac.new(self.secret, encoded, hashlib.sha256).hexdigest()
        return encoded.hex() + "." + signature

    def verify(self, token: str, plan: ActionPlan) -> None:
        try:
            encoded_hex, supplied_signature = token.split(".", 1)
            encoded = bytes.fromhex(encoded_hex)
            payload = json.loads(encoded.decode("utf-8"))
        except (ValueError, json.JSONDecodeError) as exc:
            raise ApprovalError("Malformed approval token") from exc

        expected_signature = hmac.new(self.secret, encoded, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_signature, supplied_signature):
            raise ApprovalError("Invalid approval signature")
        if int(payload.get("expires", 0)) < int(time.time()):
            raise ApprovalError("Approval token has expired")

        expected = {
            "plan_id": plan.plan_id,
            "action": plan.action,
            "target": plan.target,
            "actor": plan.actor,
            "parameters": plan.parameters,
        }
        actual = {key: payload.get(key) for key in expected}
        if actual != expected:
            raise ApprovalError("Approval token does not match the action plan")


class SSHRunner:
    def __init__(self, connect_timeout: int = 10, command_timeout: int = 60):
        self.connect_timeout = connect_timeout
        self.command_timeout = command_timeout

    def _ssh_prefix(self, host: Host) -> list[str]:
        command = [
            "ssh",
            "-o", "BatchMode=yes",
            "-o", f"ConnectTimeout={self.connect_timeout}",
            "-o", "StrictHostKeyChecking=yes" if host.verify_host_key else "StrictHostKeyChecking=accept-new",
            "-p", str(host.port),
        ]
        if host.ssh_identity_file:
            command.extend(["-i", os.path.expanduser(host.ssh_identity_file)])
        command.append(f"{host.user}@{host.address}")
        return command

    def run(self, host: Host, remote_argv: list[str], timeout: int | None = None) -> subprocess.CompletedProcess[str]:
        # Remote command arguments originate only from registered action factories.
        remote_command = " ".join(_shell_quote(value) for value in remote_argv)
        try:
            return subprocess.run(
                [*self._ssh_prefix(host), remote_command],
                capture_output=True,
                text=True,
                timeout=timeout or self.command_timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ExecutionError(f"SSH command timed out on {host.name}") from exc

    def reachable(self, host: Host) -> bool:
        result = self.run(host, ["true"], timeout=self.connect_timeout + 5)
        return result.returncode == 0

    def verify_reboot(self, host: Host, disappear_timeout: int = 90, recovery_timeout: int = 300) -> bool:
        disappear_deadline = time.time() + disappear_timeout
        disappeared = False
        while time.time() < disappear_deadline:
            if not self.reachable(host):
                disappeared = True
                break
            time.sleep(5)
        if not disappeared:
            return False

        recovery_deadline = time.time() + recovery_timeout
        while time.time() < recovery_deadline:
            if self.reachable(host):
                return True
            time.sleep(10)
        return False


def _shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _no_parameters(host: Host, parameters: dict[str, Any]) -> None:
    if parameters:
        raise ValidationError("This action does not accept parameters")


def _validate_service(host: Host, parameters: dict[str, Any]) -> None:
    service = parameters.get("service")
    if not isinstance(service, str) or service not in host.services:
        raise ValidationError(f"Service is not allowlisted for {host.name}: {service}")


def _validate_container(host: Host, parameters: dict[str, Any]) -> None:
    container = parameters.get("container")
    if not isinstance(container, str) or container not in host.containers:
        raise ValidationError(f"Container is not allowlisted for {host.name}: {container}")


def action_registry() -> dict[str, ActionDefinition]:
    return {
        "host.status": ActionDefinition(
            name="host.status",
            risk="low",
            requires_approval=False,
            description="Check SSH reachability, hostname, uptime and boot time.",
            command_factory=lambda host, params: ["sh", "-c", "hostname; uptime -p; who -b"],
            validator=_no_parameters,
        ),
        "host.reboot": ActionDefinition(
            name="host.reboot",
            risk="high",
            requires_approval=True,
            description="Reboot a Linux host and verify that it returns over SSH.",
            command_factory=lambda host, params: ["sudo", "-n", "systemctl", "reboot"],
            validator=_no_parameters,
            verify_recovery=True,
        ),
        "service.restart": ActionDefinition(
            name="service.restart",
            risk="medium",
            requires_approval=True,
            description="Restart an allowlisted systemd service.",
            command_factory=lambda host, params: ["sudo", "-n", "systemctl", "restart", params["service"]],
            validator=_validate_service,
        ),
        "docker.restart": ActionDefinition(
            name="docker.restart",
            risk="medium",
            requires_approval=True,
            description="Restart an allowlisted Docker container.",
            command_factory=lambda host, params: ["docker", "restart", params["container"]],
            validator=_validate_container,
        ),
        "system.updates_check": ActionDefinition(
            name="system.updates_check",
            risk="low",
            requires_approval=False,
            description="Report pending Debian or Ubuntu package updates.",
            command_factory=lambda host, params: ["sh", "-c", "apt list --upgradable 2>/dev/null | tail -n +2"],
            validator=_no_parameters,
        ),
    }


class OperationsEngine:
    def __init__(
        self,
        inventory: Inventory,
        audit: AuditLog,
        signer: ApprovalSigner,
        runner: SSHRunner | None = None,
    ):
        self.inventory = inventory
        self.audit = audit
        self.signer = signer
        self.runner = runner or SSHRunner()
        self.actions = action_registry()

    def plan(self, action_name: str, target: str, actor: str, parameters: dict[str, Any] | None = None) -> tuple[ActionPlan, str | None]:
        action = self.actions.get(action_name)
        if action is None:
            raise ValidationError(f"Unknown action: {action_name}")
        host = self.inventory.get(target)
        params = parameters or {}
        if action.validator:
            action.validator(host, params)
        plan = ActionPlan(
            plan_id=secrets.token_urlsafe(18),
            action=action.name,
            target=host.name,
            actor=actor,
            risk=action.risk,
            requires_approval=action.requires_approval,
            description=action.description,
            parameters=params,
            expires_at_epoch=int(time.time()) + self.signer.ttl_seconds,
        )
        token = self.signer.issue(plan) if action.requires_approval else None
        self.audit.write("action.planned", {"plan": asdict(plan)})
        return plan, token

    def execute(self, plan: ActionPlan, approval_token: str | None = None) -> ActionResult:
        action = self.actions.get(plan.action)
        if action is None:
            raise ValidationError(f"Unknown action: {plan.action}")
        host = self.inventory.get(plan.target)
        if action.validator:
            action.validator(host, plan.parameters)
        if action.requires_approval:
            if not approval_token:
                raise ApprovalError("Approval token is required")
            self.signer.verify(approval_token, plan)
            self.audit.write("action.approved", {"plan_id": plan.plan_id, "actor": plan.actor})

        remote_argv = action.command_factory(host, plan.parameters)
        started = datetime.now(timezone.utc).isoformat()
        self.audit.write(
            "action.started",
            {"plan_id": plan.plan_id, "action": plan.action, "target": plan.target, "actor": plan.actor},
        )
        completed = self.runner.run(host, remote_argv)

        recovery_verified: bool | None = None
        success = completed.returncode == 0
        if action.verify_recovery and success:
            recovery_verified = self.runner.verify_reboot(host)
            success = recovery_verified

        result = ActionResult(
            plan_id=plan.plan_id,
            action=plan.action,
            target=plan.target,
            status="completed" if success else "failed",
            started_at=started,
            completed_at=datetime.now(timezone.utc).isoformat(),
            exit_code=completed.returncode,
            stdout=completed.stdout[-8000:],
            stderr=completed.stderr[-8000:],
            recovery_verified=recovery_verified,
        )
        self.audit.write("action.completed", {"result": asdict(result)})
        if not success:
            raise ExecutionError(json.dumps(asdict(result), ensure_ascii=False))
        return result
