"""Helpers HTTP : session préconfigurée avec retry et un User-Agent poli."""
from __future__ import annotations

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

USER_AGENT = "Vigistock/0.1 (open-source project)"


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    return s


@retry(
    reraise=True,
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((requests.RequestException,)),
)
def get_json(url: str, *, params: dict | None = None, timeout: int = 30) -> dict:
    """GET avec backoff exponentiel. Lève une exception sur 4xx après les tentatives."""
    resp = session().get(url, params=params, timeout=timeout)
    resp.raise_for_status()
    return resp.json()
