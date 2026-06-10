"""One-time OAuth setup — opens browser, saves token.json for MCP.

Run from project root:
    python backend/credentials/auth_setup.py

Or from backend/:
    python credentials/auth_setup.py
"""

from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

# Scopes for Gmail + Calendar (see atlas_mcp_oauth_setup.md)
# gmail.modify is required for mark-read, archive, delete, and label actions.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
]

CREDENTIALS_DIR = Path(__file__).resolve().parent
CLIENT_SECRET = CREDENTIALS_DIR / "client_secret.json"
TOKEN_FILE = CREDENTIALS_DIR / "token.json"


def main() -> None:
    if not CLIENT_SECRET.exists():
        raise FileNotFoundError(
            f"Place your Google OAuth JSON at:\n  {CLIENT_SECRET}\n"
            "(Download from Google Cloud Console → Credentials → Desktop app)"
        )

    print("Opening browser for Google OAuth login...")
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), scopes=SCOPES)
    creds = flow.run_local_server(port=0)

    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else SCOPES,
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
    }

    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        import json
        json.dump(token_data, f, indent=2)

    print(f"Token saved to {TOKEN_FILE}")
    print("Gmail + Calendar ready — restart the backend.")
    print("If you added new scopes, delete token.json first and re-run this script.")


if __name__ == "__main__":
    main()
