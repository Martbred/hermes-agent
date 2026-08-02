from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from .core import ActionPlan, ApprovalSigner, AuditLog, Inventory, OperationsEngine, OpsError


def build_engine(args: argparse.Namespace) -> OperationsEngine:
    secret = os.environ.get("HERMES_OPS_APPROVAL_SECRET")
    if not secret:
        raise RuntimeError("HERMES_OPS_APPROVAL_SECRET is not set")
    return OperationsEngine(
        inventory=Inventory.load(args.inventory),
        audit=AuditLog(args.audit_log),
        signer=ApprovalSigner(secret, ttl_seconds=args.approval_ttl),
    )


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Hermes Homelab Operations CLI")
    root.add_argument("--inventory", default="config/inventory.json")
    root.add_argument("--audit-log", default="data/audit.jsonl")
    root.add_argument("--approval-ttl", type=int, default=300)
    commands = root.add_subparsers(dest="command", required=True)

    commands.add_parser("inventory")
    commands.add_parser("actions")

    plan = commands.add_parser("plan")
    plan.add_argument("action")
    plan.add_argument("target")
    plan.add_argument("--actor", required=True)
    plan.add_argument("--parameter", action="append", default=[], metavar="KEY=VALUE")
    plan.add_argument("--save-plan")

    execute = commands.add_parser("execute")
    execute.add_argument("--plan-file", required=True)
    execute.add_argument("--approval-token")

    return root


def parse_parameters(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"Invalid parameter, expected KEY=VALUE: {value}")
        key, item = value.split("=", 1)
        result[key] = item
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        engine = build_engine(args)
        if args.command == "inventory":
            print(json.dumps([asdict(host) for host in engine.inventory.list()], indent=2))
            return 0
        if args.command == "actions":
            data = {
                name: {
                    "risk": action.risk,
                    "requires_approval": action.requires_approval,
                    "description": action.description,
                }
                for name, action in sorted(engine.actions.items())
            }
            print(json.dumps(data, indent=2))
            return 0
        if args.command == "plan":
            plan, token = engine.plan(
                args.action,
                args.target,
                args.actor,
                parse_parameters(args.parameter),
            )
            payload = {"plan": asdict(plan), "approval_token": token}
            if args.save_plan:
                Path(args.save_plan).write_text(json.dumps(asdict(plan), indent=2), encoding="utf-8")
            print(json.dumps(payload, indent=2))
            return 0
        if args.command == "execute":
            plan = ActionPlan(**json.loads(Path(args.plan_file).read_text(encoding="utf-8")))
            result = engine.execute(plan, args.approval_token)
            print(json.dumps(asdict(result), indent=2))
            return 0
        return 2
    except (OpsError, RuntimeError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
