# Extract Entra + GitHub Copilot Info

This project extracts:
- Microsoft Graph user information
- Microsoft Entra groups, group members, and role assignments (Admin vs User)
- GitHub Copilot seat and usage information

## API endpoints used
- GET https://graph.microsoft.com/v1.0/users/{user-id}
- GET https://graph.microsoft.com/v1.0/users/{user-id}/manager
- GET https://graph.microsoft.com/v1.0/users
- GET https://graph.microsoft.com/v1.0/groups
- GET https://graph.microsoft.com/v1.0/groups/{group-id}/members
- GET https://graph.microsoft.com/v1.0/directoryRoles
- GET https://graph.microsoft.com/v1.0/directoryRoles/{role-id}/members
- GET https://api.github.com/orgs/{org}/copilot/billing/seats
- GET https://api.github.com/enterprises/{enterprise}/copilot/billing/seats

## Folder structure
- src/extract_az_entra_info/clients.py
- src/extract_az_entra_info/io_utils.py
- src/extract_az_entra_info/main.py
- run.py
- output/

The output folder is auto-created at runtime.

## Prerequisites

- Python 3.9 or later
- A **Microsoft Graph token** with at least these delegated/app permissions:
  `User.Read.All`, `Directory.Read.All`, `Group.Read.All`
- A **GitHub Personal Access Token (PAT)** with `read:org` and `manage_billing:copilot` scopes
  (or enterprise billing read access for enterprise targets)

> **Tip – get a Graph token quickly with the Azure CLI:**
> ```bash
> az login
> az account get-access-token --resource https://graph.microsoft.com --query accessToken -o tsv
> ```

---

## Setup

### 1. Clone / download the project

```bash
git clone <repo-url>
cd Extract-AZ-Info
```

### 2. Create and activate a virtual environment

**Windows (PowerShell)**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure credentials

```bash
cp .env.example .env   # Windows: copy .env.example .env
```

Open `.env` and fill in your tokens:

```dotenv
GRAPH_TOKEN="<your-microsoft-graph-bearer-token>"
GITHUB_TOKEN="<your-github-personal-access-token>"
```

Tokens can also be passed directly as CLI arguments (see below), which takes precedence over `.env`.

---

## Run

### GitHub Organization

```bash
python run.py --user-id user@contoso.com --org my-github-org
```

### GitHub Enterprise

```bash
python run.py --user-id user@contoso.com --enterprise my-github-enterprise
```

### All available arguments

| Argument | Required | Default | Description |
|---|---|---|---|
| `--user-id` | Yes | — | User UPN or object ID for the Graph lookup (e.g. `user@contoso.com`) |
| `--org` | One of org/enterprise | — | GitHub organization slug |
| `--enterprise` | One of org/enterprise | — | GitHub enterprise slug |
| `--output-dir` | No | `output` | Folder where extracted files are written |
| `--activity-window-days` | No | `30` | Users active within N days are counted as active |
| `--graph-token` | No | reads `GRAPH_TOKEN` from `.env` | Override the Graph bearer token inline |
| `--github-token` | No | reads `GITHUB_TOKEN` from `.env` | Override the GitHub PAT inline |

### Example with all options

```bash
python run.py \
  --user-id admin@contoso.com \
  --org my-github-org \
  --output-dir results \
  --activity-window-days 90
```

---

## Output files

All files are written to `--output-dir` (default: `output/`):

| File | Description |
|---|---|
| `entra_user_data.json` | Raw Graph user + manager data |
| `entra_directory_data.json` | Groups, members, and directory roles |
| `entra_group_users_roles.csv` | Flat CSV of group membership and admin/user roles |
| `copilot_usage_data.json` | Raw Copilot seat data from GitHub |
| `copilot_seats.csv` | Flat CSV of Copilot seat assignments |
| `combined_data.json` | Merged dataset (Entra + Copilot) |
| `report.html` | Self-contained HTML summary report |

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `Missing Graph token` | `GRAPH_TOKEN` not set | Set it in `.env` or pass `--graph-token` |
| `Missing GitHub token` | `GITHUB_TOKEN` not set | Set it in `.env` or pass `--github-token` |
| `Provide either --org or --enterprise` | Neither flag supplied | Add `--org` or `--enterprise` |
| `Use only one of --org or --enterprise` | Both flags supplied | Remove one |
| HTTP 401 from Graph | Token expired or wrong resource | Re-acquire the token (see Prerequisites above) |
| HTTP 403 from GitHub | PAT missing scopes | Regenerate PAT with `read:org` + `manage_billing:copilot` |

## Output files
- output/entra_user_data.json
- output/entra_directory_data.json
- output/entra_group_users_roles.csv
- output/copilot_usage_data.json
- output/combined_data.json
- output/copilot_seats.csv
- output/report.html

## Required API permissions
Microsoft Graph token should be allowed to read users, groups, and directory roles.
GitHub token should be allowed to read organization Copilot billing seat data.
