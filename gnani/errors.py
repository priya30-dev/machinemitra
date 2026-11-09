"""Turn the three different Gnani error shapes into one readable exception.

Shapes documented at docs.gnani.ai:
  STT:            {"success": false, "error": {"type": ..., "message": ...}}
  TTS:            {"success": false, "message": ..., "status_code": ...}
  Auth / limits:  {"detail": {"error_code": ..., "message": ..., "status_code": ...}}
  Validation:     {"detail": [ ... ]}   (422)
"""
import time

import requests


class GnaniError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message
        super().__init__(f"[{status} {code}] {message}")

    @property
    def friendly(self) -> str:
        if self.status == 401:
            return "The Gnani API key is missing or invalid. Check GNANI_API_KEY."
        if self.status == 402:
            return "Gnani credits are exhausted for this demo."
        if self.status == 429:
            return "Gnani is busy with another request. Please try again in a moment."
        if self.code == "MAX_AUDIO_DURATION_EXCEEDED":
            return "That clip is too long for one request."
        return f"Gnani returned an error: {self.message}"


def parse_error(resp: requests.Response) -> GnaniError:
    try:
        body = resp.json()
    except ValueError:
        return GnaniError(resp.status_code, "HTTP_ERROR", resp.text[:200])

    if isinstance(body.get("error"), dict):  # STT envelope
        err = body["error"]
        return GnaniError(resp.status_code, err.get("type", "ERROR"), err.get("message", ""))
    detail = body.get("detail")
    if isinstance(detail, dict):  # auth / rate limit
        return GnaniError(resp.status_code, detail.get("error_code", "ERROR"), detail.get("message", ""))
    if isinstance(detail, list):  # 422 validation
        return GnaniError(resp.status_code, "VALIDATION_ERROR", str(detail)[:300])
    if "code" in body:  # 504 gateway shape
        return GnaniError(resp.status_code, body.get("code", "ERROR"), body.get("message", ""))
    return GnaniError(resp.status_code, "ERROR", body.get("message", str(body)[:200]))


def post_with_retry(url: str, *, retries: int = 3, **kwargs) -> requests.Response:
    """POST with backoff on 429/5xx. The docs say 429 has no Retry-After header,
    so we wait 1s, 2s, 4s. Retries are kept low to protect credits."""
    delay = 1.0
    for attempt in range(retries + 1):
        resp = requests.post(url, **kwargs)
        if resp.status_code == 200:
            return resp
        if resp.status_code in (429, 500, 503, 504) and attempt < retries:
            time.sleep(delay)
            delay *= 2
            continue
        raise parse_error(resp)
    raise parse_error(resp)  # pragma: no cover
