from __future__ import annotations

import csv
import json
from html import escape
from pathlib import Path
from typing import Any


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    if not rows:
        with path.open("w", encoding="utf-8", newline="") as f:
            f.write("")
        return

    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


def _render_table(title: str, rows: list[dict[str, Any]], columns: list[str]) -> str:
    header_cells = "".join(f"<th>{escape(col)}</th>" for col in columns)
    body_rows: list[str] = []

    for row in rows:
        data_cells = "".join(
            f"<td>{escape(_as_str(row.get(col)))}</td>" for col in columns
        )
        body_rows.append(f"<tr>{data_cells}</tr>")

    if not body_rows:
        body_rows.append(
            f"<tr><td colspan=\"{len(columns)}\">No data</td></tr>"
        )

    return (
        f"<section class=\"panel\"><h2>{escape(title)}</h2>"
        f"<div class=\"table-wrap\"><table>"
        f"<thead><tr>{header_cells}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        f"</table></div></section>"
    )


def write_html_report(path: Path, combined: dict[str, Any]) -> None:
    ensure_dir(path.parent)

    graph = combined.get("graph", {})
    directory = combined.get("entra_directory", {})
    copilot = combined.get("github_copilot", {})

    profile_rows = [
        {
            "user_name": graph.get("user_name"),
            "first_name": graph.get("first_name"),
            "last_name": graph.get("last_name"),
            "user_type": graph.get("user_type"),
            "department": graph.get("department"),
            "manager": (graph.get("manager") or {}).get("name") if isinstance(graph.get("manager"), dict) else "",
            "employee_upn": (graph.get("employee_details") or {}).get("upn") if isinstance(graph.get("employee_details"), dict) else "",
            "employee_email": (graph.get("employee_details") or {}).get("email") if isinstance(graph.get("employee_details"), dict) else "",
            "job_title": (graph.get("employee_details") or {}).get("job_title") if isinstance(graph.get("employee_details"), dict) else "",
            "office_location": (graph.get("employee_details") or {}).get("office_location") if isinstance(graph.get("employee_details"), dict) else "",
            "company_name": (graph.get("employee_details") or {}).get("company_name") if isinstance(graph.get("employee_details"), dict) else "",
        }
    ]

    group_summary_rows = []
    group_member_rows = []
    for group in directory.get("groups", []) if isinstance(directory, dict) else []:
        if not isinstance(group, dict):
            continue
        group_summary_rows.append(
            {
                "group_name": group.get("name"),
                "group_id": group.get("id"),
                "user_count": group.get("user_count"),
            }
        )

        for member in group.get("users", []) if isinstance(group.get("users"), list) else []:
            if not isinstance(member, dict):
                continue
            group_member_rows.append(
                {
                    "group_name": group.get("name"),
                    "user_name": member.get("name"),
                    "first_name": member.get("first_name"),
                    "last_name": member.get("last_name"),
                    "user_upn": member.get("upn"),
                    "user_email": member.get("email"),
                    "user_type": member.get("user_type"),
                    "job_title": member.get("job_title"),
                    "department": member.get("department"),
                    "company_name": member.get("company_name"),
                    "employee_id": member.get("employee_id"),
                    "employee_type": member.get("employee_type"),
                    "role_category": member.get("role_category"),
                    "assigned_roles": member.get("assigned_roles", []),
                }
            )

    role_rows = []
    roles_obj = directory.get("roles", {}) if isinstance(directory, dict) else {}
    for role in roles_obj.get("items", []) if isinstance(roles_obj, dict) else []:
        if not isinstance(role, dict):
            continue
        role_rows.append(
            {
                "role_name": role.get("name"),
                "role_id": role.get("id"),
                "member_count": role.get("member_count"),
            }
        )

    user_summary = directory.get("user_roles_summary", {}) if isinstance(directory, dict) else {}
    admin_rows = user_summary.get("admins", []) if isinstance(user_summary, dict) else []
    standard_user_rows = user_summary.get("users", []) if isinstance(user_summary, dict) else []

    usage = copilot.get("usage_metrics", {}) if isinstance(copilot, dict) else {}
    copilot_summary_rows = [
        {
            "activity_window_days": usage.get("activity_window_days"),
            "total_seats": usage.get("total_seats"),
            "active_users": usage.get("active_users"),
            "inactive_users": usage.get("inactive_users"),
            "active_percent": usage.get("active_percent"),
        }
    ]

    copilot_seat_rows = copilot.get("seats", []) if isinstance(copilot, dict) else []
    copilot_error = copilot.get("error", "") if isinstance(copilot, dict) else ""
    directory_error = directory.get("error", "") if isinstance(directory, dict) else ""

    sections = [
        _render_table(
            "User Profile",
            profile_rows,
            [
                "user_name",
                "first_name",
                "last_name",
                "user_type",
                "department",
                "manager",
                "employee_upn",
                "employee_email",
                "job_title",
                "office_location",
                "company_name",
            ],
        ),
        _render_table(
            "Groups Summary",
            group_summary_rows,
            ["group_name", "group_id", "user_count"],
        ),
        _render_table(
            "Group Members",
            group_member_rows,
            [
                "group_name",
                "user_name",
                "first_name",
                "last_name",
                "user_upn",
                "user_email",
                "user_type",
                "job_title",
                "department",
                "company_name",
                "employee_id",
                "employee_type",
                "role_category",
                "assigned_roles",
            ],
        ),
        _render_table(
            "Directory Roles",
            role_rows,
            ["role_name", "role_id", "member_count"],
        ),
        _render_table(
            "Admins",
            [row for row in admin_rows if isinstance(row, dict)],
            [
                "name",
                "first_name",
                "last_name",
                "upn",
                "email",
                "user_type",
                "job_title",
                "department",
                "company_name",
                "employee_id",
                "employee_type",
                "assigned_roles",
            ],
        ),
        _render_table(
            "Users",
            [row for row in standard_user_rows if isinstance(row, dict)],
            [
                "name",
                "first_name",
                "last_name",
                "upn",
                "email",
                "user_type",
                "job_title",
                "department",
                "company_name",
                "employee_id",
                "employee_type",
                "assigned_roles",
            ],
        ),
        _render_table(
            "Copilot Usage Summary",
            copilot_summary_rows,
            [
                "activity_window_days",
                "total_seats",
                "active_users",
                "inactive_users",
                "active_percent",
            ],
        ),
        _render_table(
            "Copilot Seats",
            [row for row in copilot_seat_rows if isinstance(row, dict)],
            [
                "seat_assigned",
                "assignee_login",
                "assignee_id",
                "assignee_type",
                "last_activity",
                "is_active",
                "plan_type",
            ],
        ),
    ]

    html = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Entra and Copilot Report</title>
  <style>
    :root {{
      --bg: #f6f8fb;
      --panel: #ffffff;
      --text: #0f172a;
      --muted: #475569;
      --border: #dbe3ef;
      --accent: #0b5cab;
      --warn: #9a3412;
    }}
    body {{
      margin: 0;
      font-family: Segoe UI, Tahoma, sans-serif;
      color: var(--text);
      background: linear-gradient(140deg, #eef4ff 0%, var(--bg) 55%, #fdf8f2 100%);
    }}
    .container {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 24px;
    }}
    h1 {{
      margin: 0 0 6px;
      color: var(--accent);
      font-size: 30px;
    }}
    .sub {{
      margin: 0 0 18px;
      color: var(--muted);
    }}
    .warn {{
      margin: 8px 0;
      padding: 10px 12px;
      border: 1px solid #fdba74;
      background: #fff7ed;
      color: var(--warn);
      border-radius: 8px;
      white-space: pre-wrap;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 14px;
      margin-bottom: 16px;
      box-shadow: 0 5px 18px rgba(15, 23, 42, 0.06);
    }}
    h2 {{
      margin: 0 0 10px;
      font-size: 18px;
    }}
    .table-wrap {{
      overflow-x: auto;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 720px;
    }}
    th, td {{
      border: 1px solid var(--border);
      padding: 8px 10px;
      text-align: left;
      vertical-align: top;
      font-size: 14px;
    }}
    th {{
      background: #eef5ff;
      color: #0b2e59;
      position: sticky;
      top: 0;
    }}
  </style>
</head>
<body>
  <div class=\"container\">
    <h1>Entra and GitHub Copilot Report</h1>
    <p class=\"sub\">Generated from combined_data.json</p>
    {f'<div class="warn">Directory warning: {escape(_as_str(directory_error))}</div>' if directory_error else ''}
    {f'<div class="warn">Copilot warning: {escape(_as_str(copilot_error))}</div>' if copilot_error else ''}
    {''.join(sections)}
  </div>
</body>
</html>
"""

    with path.open("w", encoding="utf-8") as f:
        f.write(html)
