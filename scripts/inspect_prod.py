#!/usr/bin/env python3
"""Read-only production Supabase inspector. This module only issues HTTP GET."""

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from dotenv import dotenv_values


CONFIG_PATH = Path("/Users/matejbolta/.config/cubedbot/prod-readonly.env")
EXPECTED_PROJECT_REF = "rcrhzlaartdajijumvlj"


def load_config(path=CONFIG_PATH):
    config = dotenv_values(path)
    url = str(config.get("CUBEDBOT_PROD_SUPA_URL") or "").rstrip("/")
    key = str(config.get("CUBEDBOT_PROD_SUPA_KEY") or "")
    hostname = urlparse(url).hostname or ""
    if hostname != f"{EXPECTED_PROJECT_REF}.supabase.co":
        raise ValueError("production Supabase URL does not match the expected project")
    if not key:
        raise ValueError("production Supabase key is missing")
    return url, key


def get_rows(table, params, path=CONFIG_PATH):
    url, key = load_config(path)
    response = requests.get(
        f"{url}/rest/v1/{table}",
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
        params=params,
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise ValueError("production response was not a row list")
    return payload


def nested_value(value, path):
    for part in path.split(".") if path else []:
        if not isinstance(value, dict) or part not in value:
            raise KeyError(f"missing path component: {part}")
        value = value[part]
    return value


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    vars_parser = subparsers.add_parser("vars")
    vars_parser.add_argument("id", type=int)
    vars_parser.add_argument("--path", default="")

    user_parser = subparsers.add_parser("user")
    user_parser.add_argument("user_id", type=int)
    user_parser.add_argument("--path", default="")

    logs_parser = subparsers.add_parser("logs")
    logs_parser.add_argument("--hours", type=int, default=24)
    logs_parser.add_argument("--limit", type=int, default=500)
    return parser.parse_args()


def main():
    args = parse_args()
    if args.command == "vars":
        rows = get_rows("vars", {
            "id": f"eq.{args.id}",
            "select": "id,data",
        })
        value = rows[0] if rows else None
        if args.path and value is not None:
            value = nested_value(value.get("data"), args.path)
    elif args.command == "user":
        rows = get_rows("main", {
            "user_id": f"eq.{args.user_id}",
            "select": "*",
        })
        value = rows[0] if rows else None
        if args.path and value is not None:
            value = nested_value(value, args.path)
    else:
        if args.hours < 1 or not 1 <= args.limit <= 5000:
            raise ValueError("hours must be positive and limit must be 1..5000")
        cutoff = datetime.now(timezone.utc) - timedelta(hours=args.hours)
        value = get_rows("bot_logs", {
            "created_at": f"gte.{cutoff.isoformat()}",
            "select": "created_at,level,stream,message",
            "order": "created_at.desc",
            "limit": str(args.limit),
        })
    print(json.dumps(value, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
