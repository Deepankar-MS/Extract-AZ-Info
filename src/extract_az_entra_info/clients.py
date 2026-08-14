from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import requests


class ApiError(RuntimeError):
    pass


def _raise_for_status(response: requests.Response, context: str) -> None:
    if response.ok:
        return

    body = ""
    try:
        body = response.text
    except Exception:
        body = "<unavailable body>"

    raise ApiError(
        f"{context} failed with status {response.status_code}: {body}"
    )


@dataclass
class GraphClient:
    token: str
    base_url: str = "https://graph.microsoft.com/v1.0"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        }

    def _get_all_pages(
        self,
        url: str,
        context: str,
        params: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        next_url: str | None = url
        next_params = params

        while next_url:
            response = requests.get(
                next_url,
                headers=self._headers(),
                params=next_params,
                timeout=30,
            )
            _raise_for_status(response, context)

            payload = response.json()
            items.extend(payload.get("value", []))
            next_url = payload.get("@odata.nextLink")
            next_params = None

        return items

    def get_user_profile(self, user_id: str) -> dict[str, Any]:
        select_fields = [
            "id",
            "displayName",
            "givenName",
            "surname",
            "userPrincipalName",
            "mail",
            "userType",
            "department",
            "jobTitle",
            "employeeId",
            "employeeType",
            "officeLocation",
            "companyName",
        ]

        url = f"{self.base_url}/users/{user_id}"
        response = requests.get(
            url,
            headers=self._headers(),
            params={"$select": ",".join(select_fields)},
            timeout=30,
        )
        _raise_for_status(response, "Microsoft Graph user lookup")
        return response.json()

    def get_manager(self, user_id: str) -> dict[str, Any] | None:
        url = f"{self.base_url}/users/{user_id}/manager"
        response = requests.get(
            url,
            headers=self._headers(),
            params={"$select": "id,displayName,userPrincipalName,mail"},
            timeout=30,
        )

        if response.status_code == 404:
            return None

        _raise_for_status(response, "Microsoft Graph manager lookup")
        return response.json()

    def list_groups(self) -> list[dict[str, Any]]:
        return self._get_all_pages(
            f"{self.base_url}/groups",
            "Microsoft Graph groups lookup",
            params={"$select": "id,displayName", "$top": "999"},
        )

    def list_group_user_members(self, group_id: str) -> list[dict[str, Any]]:
        members = self._get_all_pages(
            f"{self.base_url}/groups/{group_id}/members",
            "Microsoft Graph group members lookup",
            params={
                "$select": (
                    "id,displayName,givenName,surname,userPrincipalName,mail,"
                    "userType,jobTitle,department,companyName,employeeId,employeeType"
                ),
                "$top": "999",
            },
        )

        return [
            member
            for member in members
            if member.get("@odata.type") == "#microsoft.graph.user"
        ]

    def list_directory_roles(self) -> list[dict[str, Any]]:
        return self._get_all_pages(
            f"{self.base_url}/directoryRoles",
            "Microsoft Graph directory roles lookup",
            params={"$select": "id,displayName"},
        )

    def list_directory_role_members(self, role_id: str) -> list[dict[str, Any]]:
        members = self._get_all_pages(
            f"{self.base_url}/directoryRoles/{role_id}/members",
            "Microsoft Graph directory role members lookup",
            params={
                "$select": (
                    "id,displayName,givenName,surname,userPrincipalName,mail,"
                    "userType,jobTitle,department,companyName,employeeId,employeeType"
                )
            },
        )

        return [
            member
            for member in members
            if member.get("@odata.type") == "#microsoft.graph.user"
        ]

    def list_users(self) -> list[dict[str, Any]]:
        return self._get_all_pages(
            f"{self.base_url}/users",
            "Microsoft Graph users lookup",
            params={
                "$select": (
                    "id,displayName,givenName,surname,userPrincipalName,mail,userType,"
                    "jobTitle,department,companyName,employeeId,employeeType"
                ),
                "$top": "999",
            },
        )


@dataclass
class GitHubCopilotClient:
    token: str
    base_url: str = "https://api.github.com"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _get_copilot_seats_paginated(
        self,
        endpoint: str,
        scope_label: str,
        target: str,
    ) -> list[dict[str, Any]]:
        seats: list[dict[str, Any]] = []
        page = 1

        while True:
            response = requests.get(
                f"{self.base_url}/{endpoint}",
                headers=self._headers(),
                params={"per_page": 100, "page": page},
                timeout=30,
            )
            if response.status_code in (401, 403, 404):
                hint = (
                    f"Check that the {scope_label} name is correct and the token has permission "
                    f"to access Copilot billing seats for this {scope_label}. GitHub often returns "
                    "404 for private resources when the token lacks required visibility/permissions."
                )
                raise ApiError(
                    f"GitHub Copilot seats lookup failed for {scope_label} '{target}' with status "
                    f"{response.status_code}. {hint} Response: {response.text}"
                )
            _raise_for_status(response, "GitHub Copilot seats lookup")

            payload = response.json()
            current = payload.get("seats", [])
            seats.extend(current)

            if len(current) < 100:
                break

            page += 1

        return seats

    def get_copilot_seats_for_org(self, org: str) -> list[dict[str, Any]]:
        return self._get_copilot_seats_paginated(
            endpoint=f"orgs/{org}/copilot/billing/seats",
            scope_label="organization",
            target=org,
        )

    def get_copilot_seats_for_enterprise(self, enterprise: str) -> list[dict[str, Any]]:
        return self._get_copilot_seats_paginated(
            endpoint=f"enterprises/{enterprise}/copilot/billing/seats",
            scope_label="enterprise",
            target=enterprise,
        )


def normalize_graph_data(user: dict[str, Any], manager: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "user_name": user.get("displayName"),
        "first_name": user.get("givenName"),
        "last_name": user.get("surname"),
        "user_type": user.get("userType"),
        "department": user.get("department"),
        "manager": None
        if not manager
        else {
            "id": manager.get("id"),
            "name": manager.get("displayName"),
            "upn": manager.get("userPrincipalName"),
            "email": manager.get("mail"),
        },
        "employee_details": {
            "id": user.get("id"),
            "display_name": user.get("displayName"),
            "first_name": user.get("givenName"),
            "last_name": user.get("surname"),
            "upn": user.get("userPrincipalName"),
            "email": user.get("mail"),
            "user_type": user.get("userType"),
            "job_title": user.get("jobTitle"),
            "department": user.get("department"),
            "employee_id": user.get("employeeId"),
            "employee_type": user.get("employeeType"),
            "office_location": user.get("officeLocation"),
            "company_name": user.get("companyName"),
        },
    }


def normalize_directory_data(
    users: list[dict[str, Any]],
    groups: list[dict[str, Any]],
    group_members_by_id: dict[str, list[dict[str, Any]]],
    roles: list[dict[str, Any]],
    role_members_by_id: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    user_by_id: dict[str, dict[str, Any]] = {}
    for user in users:
        if user.get("id"):
            user_by_id[user["id"]] = user

    assigned_roles_by_user: dict[str, set[str]] = {}
    role_rows: list[dict[str, Any]] = []
    for role in roles:
        role_name = role.get("displayName") or "<unnamed role>"
        members = role_members_by_id.get(role.get("id", ""), [])
        normalized_members: list[dict[str, Any]] = []
        for member in members:
            member_id = member.get("id")
            if member_id:
                assigned_roles_by_user.setdefault(member_id, set()).add(role_name)

            normalized_members.append(
                {
                    "id": member.get("id"),
                    "name": member.get("displayName"),
                    "first_name": member.get("givenName"),
                    "last_name": member.get("surname"),
                    "upn": member.get("userPrincipalName"),
                    "email": member.get("mail"),
                    "user_type": member.get("userType"),
                    "job_title": member.get("jobTitle"),
                    "department": member.get("department"),
                    "company_name": member.get("companyName"),
                    "employee_id": member.get("employeeId"),
                    "employee_type": member.get("employeeType"),
                }
            )

        role_rows.append(
            {
                "id": role.get("id"),
                "name": role_name,
                "member_count": len(normalized_members),
                "members": normalized_members,
            }
        )

    normalized_groups: list[dict[str, Any]] = []
    for group in groups:
        group_id = group.get("id", "")
        members = group_members_by_id.get(group_id, [])
        normalized_members: list[dict[str, Any]] = []
        for member in members:
            member_id = member.get("id")
            assigned_roles = sorted(assigned_roles_by_user.get(member_id or "", set()))
            role_category = "Admin" if assigned_roles else "User"

            normalized_members.append(
                {
                    "id": member.get("id"),
                    "name": member.get("displayName"),
                    "first_name": member.get("givenName"),
                    "last_name": member.get("surname"),
                    "upn": member.get("userPrincipalName"),
                    "email": member.get("mail"),
                    "user_type": member.get("userType"),
                    "job_title": member.get("jobTitle"),
                    "department": member.get("department"),
                    "company_name": member.get("companyName"),
                    "employee_id": member.get("employeeId"),
                    "employee_type": member.get("employeeType"),
                    "assigned_roles": assigned_roles,
                    "role_category": role_category,
                }
            )

        normalized_groups.append(
            {
                "id": group.get("id"),
                "name": group.get("displayName"),
                "user_count": len(normalized_members),
                "users": normalized_members,
            }
        )

    admins: list[dict[str, Any]] = []
    standard_users: list[dict[str, Any]] = []
    for user_id, user in user_by_id.items():
        assigned_roles = sorted(assigned_roles_by_user.get(user_id, set()))
        row = {
            "id": user.get("id"),
            "name": user.get("displayName"),
            "first_name": user.get("givenName"),
            "last_name": user.get("surname"),
            "upn": user.get("userPrincipalName"),
            "email": user.get("mail"),
            "user_type": user.get("userType"),
            "job_title": user.get("jobTitle"),
            "department": user.get("department"),
            "company_name": user.get("companyName"),
            "employee_id": user.get("employeeId"),
            "employee_type": user.get("employeeType"),
            "assigned_roles": assigned_roles,
        }

        if assigned_roles:
            admins.append(row)
        else:
            standard_users.append(row)

    return {
        "group_count": len(normalized_groups),
        "groups": normalized_groups,
        "roles": {
            "role_count": len(role_rows),
            "items": role_rows,
        },
        "user_roles_summary": {
            "admin_count": len(admins),
            "user_count": len(standard_users),
            "admins": admins,
            "users": standard_users,
        },
    }


def _parse_iso8601(value: str | None) -> datetime | None:
    if not value:
        return None

    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def normalize_copilot_data(
    seats: list[dict[str, Any]],
    activity_window_days: int,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=activity_window_days)

    normalized_seats: list[dict[str, Any]] = []
    active_users = 0

    for seat in seats:
        assignee = seat.get("assignee", {})
        last_activity_at = seat.get("last_activity_at")
        parsed_last_activity = _parse_iso8601(last_activity_at)
        is_active = bool(parsed_last_activity and parsed_last_activity >= cutoff)

        if is_active:
            active_users += 1

        normalized_seats.append(
            {
                "seat_assigned": assignee.get("login") or assignee.get("id"),
                "assignee_login": assignee.get("login"),
                "assignee_id": assignee.get("id"),
                "assignee_type": assignee.get("type"),
                "last_activity": last_activity_at,
                "is_active": is_active,
                "created_at": seat.get("created_at"),
                "updated_at": seat.get("updated_at"),
                "pending_cancellation_date": seat.get("pending_cancellation_date"),
                "plan_type": seat.get("plan_type"),
            }
        )

    total_seats = len(normalized_seats)
    inactive_users = total_seats - active_users

    return {
        "seat_assigned": total_seats,
        "last_activity": [
            {
                "assignee_login": row["assignee_login"],
                "last_activity": row["last_activity"],
            }
            for row in normalized_seats
        ],
        "active_users": active_users,
        "usage_metrics": {
            "activity_window_days": activity_window_days,
            "total_seats": total_seats,
            "active_users": active_users,
            "inactive_users": inactive_users,
            "active_percent": round((active_users / total_seats) * 100, 2)
            if total_seats
            else 0.0,
        },
        "seats": normalized_seats,
    }
