import requests

BLOCKER_BASE_URL = "http://127.0.0.1:9001"


class BlockerClientError(Exception):
    """Custom exception for structured errors."""

    def __init__(self, message, service="blocker", trace=None):
        self.message = message
        self.service = service
        self.trace = trace
        super().__init__(message)

    def to_dict(self):
        return {
            "detail": {
                "service": self.service,
                "message": self.message,
                "trace": self.trace,
            }
        }


class BlockerClient:
    """Thin wrapper for communicating with the blocker service."""

    def __init__(self, base_url=BLOCKER_BASE_URL):
        self.base_url = base_url.rstrip("/")

    # -------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------
    def _handle_response(self, resp):
        """Convert non-200 responses into structured errors."""
        if resp.status_code == 200:
            try:
                return resp.json()
            except Exception:
                raise BlockerClientError(
                    "Invalid JSON response from blocker service."
                )
        else:
            # Return an error with the body as a trace
            raise BlockerClientError(
                f"Blocker service returned {resp.status_code}",
                trace=resp.text,
            )

    def _handle_exception(self, e):
        """Convert network errors into structured errors."""
        raise BlockerClientError(
            "Blocker service not reachable",
            trace=str(e),
        )

    # -------------------------------------------------------------
    # API Methods
    # -------------------------------------------------------------
    def get_status(self):
        try:
            resp = requests.get(f"{self.base_url}/status")
            return self._handle_response(resp)
        except Exception as e:
            self._handle_exception(e)

    def start(self):
        try:
            resp = requests.post(f"{self.base_url}/start")
            return self._handle_response(resp)
        except Exception as e:
            self._handle_exception(e)

    def stop(self):
        try:
            resp = requests.post(f"{self.base_url}/stop")
            return self._handle_response(resp)
        except Exception as e:
            self._handle_exception(e)

    def reload(self):
        try:
            resp = requests.post(f"{self.base_url}/reload")
            return self._handle_response(resp)
        except Exception as e:
            self._handle_exception(e)

    def update_config(self, new_config: dict):
        try:
            resp = requests.post(f"{self.base_url}/update-config", json=new_config)
            return self._handle_response(resp)
        except Exception as e:
            self._handle_exception(e)
