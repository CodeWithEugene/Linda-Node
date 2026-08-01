import httpx

from .base import SourceAdapter


class IcpacTriggersAdapter(SourceAdapter):
    endpoint = "https://eatriggersthresholds.icpac.net/api/triggers/"

    def __init__(self, timeout_seconds: float = 10.0):
        self.timeout_seconds = timeout_seconds

    def fetch(self):
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.get(self.endpoint)
            response.raise_for_status()
        raise NotImplementedError("Live trigger response mapping is configured through the replay fallback during exercise mode.")
