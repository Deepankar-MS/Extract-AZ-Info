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

## Setup
1. Open a terminal in this project folder.
2. Create and activate a virtual environment.
3. Install dependencies:
   pip install -r requirements.txt
4. Copy .env.example to .env and set tokens:
   - GRAPH_TOKEN
   - GITHUB_TOKEN

## Run
Example:
python run.py --user-id user@contoso.com --org my-github-org

Enterprise example:
python run.py --user-id user@contoso.com --enterprise my-github-enterprise

Optional arguments:
- --output-dir output
- --activity-window-days 30
- --org <organization-slug>
- --enterprise <enterprise-slug>
- --graph-token <token>
- --github-token <token>

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
