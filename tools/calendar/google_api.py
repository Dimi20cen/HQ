from fastapi import HTTPException

IMPORT_ERROR = None

try:
    from google.auth.transport.requests import Request as GoogleAuthRequest
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except Exception as exc:  # pragma: no cover - environment dependent
    IMPORT_ERROR = str(exc)
    GoogleAuthRequest = None
    Credentials = None
    Flow = None
    HttpError = Exception
    build = None


def ensure_google_libs() -> None:
    if IMPORT_ERROR:
        raise HTTPException(
            status_code=500,
            detail=(
                "Google Calendar dependencies are not installed. "
                f"Import error: {IMPORT_ERROR}"
            ),
        )
