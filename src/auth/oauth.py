from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES_READONLY = ["https://www.googleapis.com/auth/youtube.readonly"]
SCOPES_WRITE = ["https://www.googleapis.com/auth/youtube"]


def get_credentials(
    client_secret_file: str = "client_secret.json",
    token_file: str = "token.json",
    readonly: bool = True,
) -> Credentials:
    scopes = SCOPES_READONLY if readonly else SCOPES_WRITE
    token_path = Path(token_file)
    creds = None

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(token_file, scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, scopes)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json())

    return creds


def get_youtube_client(
    client_secret_file: str = "client_secret.json",
    token_file: str = "token.json",
    readonly: bool = True,
):
    creds = get_credentials(client_secret_file, token_file, readonly)
    return build("youtube", "v3", credentials=creds)
