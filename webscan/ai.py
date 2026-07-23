"""Optional AI analysis of bypass results, via the official Anthropic SDK.

Given the working bypasses the deterministic engine found, Claude explains the
root cause in plain language and writes the exact server/.htaccess fix.

This is the ONLY part of webscan that isn't zero-dependency. It's fully
optional — the scanner works without it. To enable:

    pip install anthropic
    export ANTHROPIC_API_KEY=sk-ant-...   # or run `ant auth login`

Model defaults to Claude Opus 4.8 (claude-opus-4-8).
"""

from __future__ import annotations

import json

DEFAULT_MODEL = "claude-opus-4-8"

# JSON shape we ask Claude to return, so the UI can render it cleanly.
_SCHEMA = {
    "type": "object",
    "properties": {
        "root_cause": {"type": "string"},
        "overall_severity": {
            "type": "string",
            "enum": ["critical", "high", "medium", "low", "none"],
        },
        "summary": {"type": "string"},
        "bypasses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "technique": {"type": "string"},
                    "how_it_works": {"type": "string"},
                    "fix": {"type": "string"},
                },
                "required": ["technique", "how_it_works", "fix"],
                "additionalProperties": False,
            },
        },
        "recommended_config": {
            "type": "string",
            "description": "A concrete corrected .htaccess / server config snippet to apply.",
        },
    },
    "required": ["root_cause", "overall_severity", "summary",
                 "bypasses", "recommended_config"],
    "additionalProperties": False,
}

_SYSTEM = (
    "You are a web security engineer helping the OWNER of a website understand "
    "why a directory they locked (typically with Apache .htaccess) is still "
    "reachable, and how to lock it down properly. You are given the results of "
    "an authorized bypass test against their own server. Be precise and "
    "practical. Explain each working bypass in plain language, then give a "
    "single corrected configuration they can apply. Prefer Apache .htaccess "
    "syntax unless the evidence points to nginx/IIS. Never suggest anything "
    "offensive or aimed at third parties — this is purely defensive hardening."
)


_VERIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "is_real": {"type": "boolean"},
                    "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                    "reason": {"type": "string"},
                },
                "required": ["index", "is_real", "confidence", "reason"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["results"],
    "additionalProperties": False,
}

_VERIFY_SYSTEM = (
    "You are a web security engineer triaging the output of an authorized "
    "403-bypass test against the user's OWN server. For each candidate, decide "
    "whether the response actually served the PROTECTED resource (a genuine "
    "bypass) or is a false positive: the site's normal homepage, a generic "
    "error/404 page, a redirect to login, an empty method response, or a TRACE "
    "echo of the request. Judge from the status, content-type, requested path "
    "vs. the locked path, and the body preview. If the locked URL is an image "
    "and the response content-type is an image type with real bytes, that's a "
    "genuine bypass. Be decisive and concise."
)


class AIUnavailable(RuntimeError):
    """Raised when the SDK isn't installed or no credentials are configured."""


def available() -> tuple[bool, str]:
    """Return (ok, message) describing whether AI analysis can run."""
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False, ("The 'anthropic' package isn't installed. Run "
                       "`pip install anthropic` to enable AI explanations.")
    return True, "ready"


def _build_prompt(baseline: dict, bypasses: list) -> str:
    lines = [
        f"Target (a directory I locked on my own server): {baseline.get('url')}",
        f"Baseline response with a normal request: HTTP {baseline.get('status')} "
        f"({'forbidden/locked' if baseline.get('locked') else 'NOT forbidden'}).",
        "",
        f"The bypass tester found {len(bypasses)} request(s) that got through "
        "(returned served content where the normal request was forbidden):",
        "",
    ]
    for i, b in enumerate(bypasses, 1):
        lines.append(f"{i}. Technique: {b['technique']} [{b['category']}]")
        lines.append(f"   Request: {b['method']} {b['url']}")
        if b.get("sent_headers"):
            hdrs = ", ".join(f"{k}: {v}" for k, v in b["sent_headers"].items())
            lines.append(f"   Extra headers sent: {hdrs}")
        lines.append(f"   Result: HTTP {b['status']}"
                     + (" with directory listing" if b.get("directory_listing") else ""))
        lines.append(f"   What it did: {b['description']}")
        lines.append("")
    lines.append(
        "Explain the root cause, rate the overall severity, explain each working "
        "bypass, and give me one corrected configuration to actually lock this "
        "directory. Return it in the required JSON structure."
    )
    return "\n".join(lines)


def _client(api_key, anthropic):
    try:
        return (anthropic.Anthropic(api_key=api_key) if api_key
                else anthropic.Anthropic())
    except Exception as e:
        raise AIUnavailable(
            "Couldn't initialise the Anthropic client. Set ANTHROPIC_API_KEY "
            f"or run `ant auth login`. ({e})"
        ) from e


def _run_structured(client, anthropic, system, prompt, schema, model):
    try:
        with client.messages.stream(
            model=model, max_tokens=16000, system=system,
            thinking={"type": "adaptive"},
            output_config={"format": {"type": "json_schema", "schema": schema}},
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            message = stream.get_final_message()
    except anthropic.AuthenticationError as e:
        raise AIUnavailable(f"Anthropic authentication failed: {e}") from e
    except anthropic.RateLimitError as e:
        raise RuntimeError(f"Anthropic rate limit hit — try again shortly. ({e})") from e
    except anthropic.APIError as e:
        raise RuntimeError(f"Anthropic API error: {e}") from e
    if message.stop_reason == "refusal":
        raise RuntimeError("The model declined this request.")
    if message.stop_reason == "max_tokens":
        raise RuntimeError("The AI response was cut off (token limit) — try fewer items at once.")
    text = next((b.text for b in message.content if b.type == "text"), "")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Could not parse AI response as JSON: {e}") from e


def verify_bypasses(target_url: str, baseline: dict, candidates: list, *,
                    api_key: str | None = None, model: str = DEFAULT_MODEL) -> dict:
    """Ask Claude which candidate 'bypasses' really served the protected resource.

    `candidates` is a list of dicts with: technique, method, url (what was
    requested), sent_headers, status, content_type, body_preview. Returns
    {"results": [{index, is_real, confidence, reason}, ...]}.
    """
    try:
        import anthropic
    except ImportError as e:
        raise AIUnavailable("The 'anthropic' package isn't installed. Run `pip install anthropic`.") from e
    if not candidates:
        return {"results": []}

    client = _client(api_key, anthropic)
    lines = [
        f"Locked URL under test: {target_url}",
        f"A normal request to it returned HTTP {baseline.get('status')} "
        f"({'forbidden/locked' if baseline.get('locked') else 'not forbidden'}).",
        "",
        "Candidates (decide is_real for each by index):",
    ]
    for i, c in enumerate(candidates):
        hdrs = ", ".join(f"{k}: {v}" for k, v in (c.get("sent_headers") or {}).items()) or "none"
        prev = (c.get("body_preview") or "").strip()
        prev = (prev[:500] + "…") if len(prev) > 500 else prev
        lines += [
            f"[{i}] technique={c.get('technique')} method={c.get('method')}",
            f"    requested: {c.get('url')}   extra headers: {hdrs}",
            f"    response: HTTP {c.get('status')} content-type={c.get('content_type') or '?'}",
            f"    body preview: {prev!r}" if prev else "    body preview: (empty / binary)",
        ]
    prompt = "\n".join(lines)
    return _run_structured(client, anthropic, _VERIFY_SYSTEM, prompt, _VERIFY_SCHEMA, model)


def analyze(baseline: dict, bypasses: list, *,
            api_key: str | None = None, model: str = DEFAULT_MODEL) -> dict:
    """Analyze bypasses with Claude. Returns the parsed JSON dict.

    Raises AIUnavailable if the SDK/credentials aren't present, and surfaces the
    SDK's own exceptions (auth, rate limit, …) with readable messages.
    """
    try:
        import anthropic
    except ImportError as e:
        raise AIUnavailable(
            "The 'anthropic' package isn't installed. Run `pip install anthropic`."
        ) from e

    if not bypasses:
        return {
            "root_cause": "No bypasses were found — the lock appears to be holding.",
            "overall_severity": "none",
            "summary": "Every technique tried was blocked. If people are still "
                       "seeing the content, the route in is likely outside these "
                       "request-based tests (a cached copy, a different URL/alias, "
                       "or a search-engine snapshot from before you locked it).",
            "bypasses": [],
            "recommended_config": "",
        }

    client = _client(api_key, anthropic)
    prompt = _build_prompt(baseline, bypasses)
    return _run_structured(client, anthropic, _SYSTEM, prompt, _SCHEMA, model)
