from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from .clients import (
    ApiError,
    GraphClient,
    GitHubCopilotClient,
    normalize_copilot_data,
    normalize_directory_data,
    normalize_graph_data,
)
from .io_utils import ensure_dir, write_csv, write_json
from .io_utils import write_html_report


def _clean_token(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned = value.strip()
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (
        cleaned.startswith("'") and cleaned.endswith("'")
    ):
        cleaned = cleaned[1:-1].strip()

    return cleaned or None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract user and Copilot seat/usage data from Graph and GitHub APIs."
    )
    parser.add_argument("--user-id", required=True, help="User ID or UPN for Graph lookup")
    parser.add_argument("--org", default=None, help="GitHub organization name")
    parser.add_argument("--enterprise", default=None, help="GitHub enterprise slug")
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory where extracted files are written",
    )
    parser.add_argument(
        "--activity-window-days",
        type=int,
        default=30,
        help="Users active within this many days count as active",
    )
    parser.add_argument("--graph-token", default=None, help="Microsoft Graph bearer token")
    parser.add_argument("--github-token", default=None, help="GitHub bearer token")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()

    graph_token = _clean_token(args.graph_token or os.getenv("GRAPH_TOKEN"))
    github_token = _clean_token(
        args.github_token or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    )

    if not graph_token:
        raise SystemExit("Missing Graph token. Set GRAPH_TOKEN or pass --graph-token")
    if not github_token:
        raise SystemExit("Missing GitHub token. Set GITHUB_TOKEN or pass --github-token")
    if not args.org and not args.enterprise:
        raise SystemExit("Provide either --org or --enterprise")
    if args.org and args.enterprise:
        raise SystemExit("Use only one of --org or --enterprise")

    output_dir = Path(args.output_dir)
    ensure_dir(output_dir)

    graph_client = GraphClient(token=graph_token)
    github_client = GitHubCopilotClient(token=github_token)

    user_profile = graph_client.get_user_profile(args.user_id)
    manager_profile = graph_client.get_manager(args.user_id)

    graph_data = normalize_graph_data(user_profile, manager_profile)

    directory_error: str | None = None
    directory_data: dict[str, object] = {
        "group_count": 0,
        "groups": [],
        "roles": {"role_count": 0, "items": []},
        "user_roles_summary": {
            "admin_count": 0,
            "user_count": 0,
            "admins": [],
            "users": [],
        },
    }
    try:
        users = graph_client.list_users()
        groups = graph_client.list_groups()
        group_members_by_id = {
            group.get("id", ""): graph_client.list_group_user_members(group.get("id", ""))
            for group in groups
            if group.get("id")
        }
        roles = graph_client.list_directory_roles()
        role_members_by_id = {
            role.get("id", ""): graph_client.list_directory_role_members(role.get("id", ""))
            for role in roles
            if role.get("id")
        }

        directory_data = normalize_directory_data(
            users=users,
            groups=groups,
            group_members_by_id=group_members_by_id,
            roles=roles,
            role_members_by_id=role_members_by_id,
        )
    except ApiError as exc:
        directory_error = str(exc)
        directory_data["error"] = directory_error

    copilot_error: str | None = None
    seats: list[dict[str, object]] = []
    try:
        if args.enterprise:
            seats = github_client.get_copilot_seats_for_enterprise(args.enterprise)
        else:
            seats = github_client.get_copilot_seats_for_org(args.org)
    except ApiError as exc:
        copilot_error = str(exc)

    copilot_data = normalize_copilot_data(seats, args.activity_window_days)
    if copilot_error:
        copilot_data["error"] = copilot_error

    combined = {
        "graph": graph_data,
        "entra_directory": directory_data,
        "github_copilot": copilot_data,
    }

    group_user_rows: list[dict[str, object]] = []
    for group in directory_data.get("groups", []):
        if not isinstance(group, dict):
            continue
        group_name = group.get("name")
        users_in_group = group.get("users", [])
        if not isinstance(users_in_group, list):
            continue
        for user in users_in_group:
            if not isinstance(user, dict):
                continue
            group_user_rows.append(
                {
                    "group_name": group_name,
                    "user_name": user.get("name"),
                    "first_name": user.get("first_name"),
                    "last_name": user.get("last_name"),
                    "user_upn": user.get("upn"),
                    "user_email": user.get("email"),
                    "user_type": user.get("user_type"),
                    "job_title": user.get("job_title"),
                    "department": user.get("department"),
                    "company_name": user.get("company_name"),
                    "employee_id": user.get("employee_id"),
                    "employee_type": user.get("employee_type"),
                    "role_category": user.get("role_category"),
                    "assigned_roles": ";".join(user.get("assigned_roles", [])),
                }
            )

    write_json(output_dir / "entra_user_data.json", graph_data)
    write_json(output_dir / "entra_directory_data.json", directory_data)
    write_json(output_dir / "copilot_usage_data.json", copilot_data)
    write_json(output_dir / "combined_data.json", combined)
    write_csv(output_dir / "entra_group_users_roles.csv", group_user_rows)
    write_csv(output_dir / "copilot_seats.csv", copilot_data["seats"])
    write_html_report(output_dir / "report.html", combined)

    print(f"Wrote: {output_dir / 'entra_user_data.json'}")
    print(f"Wrote: {output_dir / 'entra_directory_data.json'}")
    print(f"Wrote: {output_dir / 'copilot_usage_data.json'}")
    print(f"Wrote: {output_dir / 'combined_data.json'}")
    print(f"Wrote: {output_dir / 'entra_group_users_roles.csv'}")
    print(f"Wrote: {output_dir / 'copilot_seats.csv'}")
    print(f"Wrote: {output_dir / 'report.html'}")
    if directory_error:
        print("Warning: Directory extraction failed; wrote partial output with error details.")
    if copilot_error:
        print("Warning: Copilot API call failed; wrote Graph data and empty Copilot seats with error details.")


if __name__ == "__main__":
    main()
