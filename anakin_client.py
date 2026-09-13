import os
import time
from typing import Any, Dict, List, Optional

import requests


class AnakinError(RuntimeError):
    pass


class AnakinClient:
    """Small REST client for Anakin.io APIs used by OpportunityScout."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANAKIN_API_KEY", "")
        self.base_url = (base_url or os.getenv("ANAKIN_BASE_URL", "https://api.anakin.io/v1")).rstrip("/")
        if not self.api_key:
            raise AnakinError("Missing ANAKIN_API_KEY. Add it to .env locally or Streamlit Secrets when deployed.")

        self.session = requests.Session()
        self.session.headers.update(
            {
                "X-API-Key": self.api_key,
                "Content-Type": "application/json",
                "User-Agent": "OpportunityScout-Agent/1.0",
            }
        )

    def _raise(self, response: requests.Response) -> None:
        if response.ok:
            return
        try:
            body = response.json()
        except Exception:
            body = response.text
        raise AnakinError(f"Anakin API error {response.status_code}: {body}")

    def search(self, prompt: str, limit: int = 8) -> List[Dict[str, Any]]:
        """Live AI-powered web search."""
        response = self.session.post(
            f"{self.base_url}/search",
            json={"prompt": prompt, "limit": max(1, min(limit, 20))},
            timeout=60,
        )
        self._raise(response)
        data = response.json()
        return data.get("results", [])

    def scrape(self, url: str, use_browser: bool = False, timeout_s: int = 90) -> Dict[str, Any]:
        """Read a page through Anakin and return clean page content."""
        response = self.session.post(
            f"{self.base_url}/url-scraper",
            json={"url": url, "useBrowser": use_browser, "generateJson": False},
            timeout=30,
        )
        self._raise(response)
        data = response.json()

        # Some deployments may return completed data inline.
        if data.get("status") == "completed" and (data.get("markdown") or data.get("cleanedHtml")):
            return data

        job_id = data.get("jobId") or data.get("job_id") or data.get("id")
        if not job_id:
            return data

        return self._poll(f"/url-scraper/{job_id}", timeout_s=timeout_s, interval=2)

    def agentic_research(self, prompt: str, timeout_s: int = 150) -> Dict[str, Any]:
        """Run Anakin's multi-stage research pipeline."""
        response = self.session.post(
            f"{self.base_url}/agentic-search",
            json={"prompt": prompt},
            timeout=30,
        )
        self._raise(response)
        data = response.json()
        job_id = data.get("job_id") or data.get("jobId") or data.get("id")
        if not job_id:
            return data
        return self._poll(f"/agentic-search/{job_id}", timeout_s=timeout_s, interval=5)

    def ask_chatgpt_via_wire(self, prompt: str, timeout_s: int = 90) -> str:
        """Use Anakin Wire's ChatGPT action so no second AI API key is required."""
        response = self.session.post(
            f"{self.base_url}/wire/task",
            json={
                "action_id": "chatgpt",
                "params": {
                    "prompt": prompt,
                    "web_search": False,
                    "include_html": False,
                },
            },
            timeout=30,
        )
        self._raise(response)
        data = response.json()
        job_id = data.get("job_id") or data.get("jobId") or data.get("id")
        if not job_id:
            return self._extract_text(data)

        result = self._poll(f"/wire/jobs/{job_id}", timeout_s=timeout_s, interval=2)
        return self._extract_text(result)

    def _poll(self, path: str, timeout_s: int, interval: int) -> Dict[str, Any]:
        started = time.time()
        last = {}
        while time.time() - started < timeout_s:
            response = self.session.get(f"{self.base_url}{path}", timeout=30)
            self._raise(response)
            last = response.json()
            status = str(last.get("status", "")).lower()
            if status == "completed":
                return last
            if status == "failed":
                raise AnakinError(last.get("error", "Anakin job failed."))
            time.sleep(interval)
        raise AnakinError(f"Timed out waiting for Anakin job after {timeout_s}s. Last response: {last}")

    @staticmethod
    def _extract_text(payload: Any) -> str:
        if isinstance(payload, str):
            return payload
        if isinstance(payload, list):
            for item in payload:
                text = AnakinClient._extract_text(item)
                if text:
                    return text
            return ""
        if not isinstance(payload, dict):
            return str(payload or "")

        preferred_keys = (
            "answer",
            "text",
            "markdown",
            "content",
            "response",
            "output",
            "message",
        )
        for key in preferred_keys:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        for key in ("result", "data", "generatedJson", "structured_data"):
            if key in payload:
                text = AnakinClient._extract_text(payload[key])
                if text:
                    return text
        return str(payload)
