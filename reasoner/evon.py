"""Client for Gnani Evon v3.3 served behind an OpenAI-compatible API.

Evon is open weights and not on Gnani's API platform yet, so we run it
ourselves (see notebooks/evon_kaggle.ipynb) with llama.cpp's llama-server and
point EVON_BASE_URL at it. Thinking is disabled for fast structured answers,
as the model card recommends for extraction tasks
(chat_template_kwargs: {"enable_thinking": false})."""
import json
import re

import requests

import config
from reasoner.prompts import (LANGUAGE_NAMES, TICKET_SYSTEM, TICKET_USER,
                              TRANSLATE_SYSTEM)
from reasoner.schema import Ticket, from_dict


class EvonUnavailable(Exception):
    pass


def _headers() -> dict:
    h = {"Content-Type": "application/json"}
    if config.EVON_API_KEY:
        h["Authorization"] = f"Bearer {config.EVON_API_KEY}"
    return h


def is_online(timeout: float = 4.0) -> bool:
    if not config.EVON_BASE_URL:
        return False
    try:
        r = requests.get(f"{config.EVON_BASE_URL}/v1/models", headers=_headers(), timeout=timeout)
        return r.status_code == 200
    except requests.RequestException:
        return False


def _chat(messages: list[dict], max_tokens: int = 900, json_mode: bool = False) -> str:
    if not config.EVON_BASE_URL:
        raise EvonUnavailable("EVON_BASE_URL is not set")
    body = {
        "model": config.EVON_MODEL,
        "messages": messages,
        "temperature": 0.3,
        "top_p": 0.95,
        "max_tokens": max_tokens,
        "chat_template_kwargs": {"enable_thinking": False},
        "stream": False,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    try:
        r = requests.post(f"{config.EVON_BASE_URL}/v1/chat/completions", headers=_headers(),
                          json=body, timeout=config.EVON_TIMEOUT)
        if r.status_code == 400 and json_mode:  # server without JSON mode support
            body.pop("response_format")
            r = requests.post(f"{config.EVON_BASE_URL}/v1/chat/completions", headers=_headers(),
                              json=body, timeout=config.EVON_TIMEOUT)
    except requests.RequestException as e:
        raise EvonUnavailable(str(e)) from e
    if r.status_code != 200:
        raise EvonUnavailable(f"HTTP {r.status_code}: {r.text[:200]}")
    content = r.json()["choices"][0]["message"].get("content") or ""
    return re.sub(r"<think>.*?</think>", "", content, flags=re.S).strip()


def extract_json(text: str) -> dict:
    """Pull the first JSON object out of a model reply, tolerating ```json fences
    and chatter before or after."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    depth = 0
    for i in range(start, len(text)) if start >= 0 else []:
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])
    raise ValueError("No JSON object found in model reply")


def make_ticket(transcript: str, context: str = "") -> Ticket:
    reply = _chat([
        {"role": "system", "content": TICKET_SYSTEM},
        {"role": "user", "content": TICKET_USER.format(transcript=transcript, context=context or "none")},
    ], json_mode=True)
    try:
        data = extract_json(reply)
    except (ValueError, json.JSONDecodeError) as e:
        raise EvonUnavailable(f"Evon reply was not valid JSON: {e}") from e
    return from_dict(data, reasoner="evon")


def translate(text: str, language: str) -> str:
    name = LANGUAGE_NAMES.get(language, "Hindi")
    return _chat([
        {"role": "system", "content": TRANSLATE_SYSTEM.format(language_name=name)},
        {"role": "user", "content": text},
    ], max_tokens=400)
