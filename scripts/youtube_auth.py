"""
YouTube OAuth2 token generator — run ONCE locally (outside Docker).

Usage:
    pip3 install google-auth-oauthlib python-dotenv
    python3 scripts/youtube_auth.py

Reads YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET from .env automatically.
Then copy the printed YOUTUBE_TOKEN_JSON line to your .env file.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

# Load .env from project root (works regardless of cwd)
load_dotenv(Path(__file__).parent.parent / ".env")

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main() -> None:
    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise SystemExit(
            "ERROR: YOUTUBE_CLIENT_ID y YOUTUBE_CLIENT_SECRET no encontrados en .env"
        )

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uris": ["http://localhost:8080"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=8080)

    print("\n✅ Auth successful! Copy this line to your .env:\n")
    print(f"YOUTUBE_TOKEN_JSON='{creds.to_json()}'")


if __name__ == "__main__":
    main()
