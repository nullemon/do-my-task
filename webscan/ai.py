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

    try:
        client = (anthropic.Anthropic(api_key=api_key) if api_key
                  else anthropic.Anthropic())
    except Exception as e:  # missing credentials surface here
        raise AIUnavailable(
            "Couldn't initialise the Anthropic client. Set ANTHROPIC_API_KEY "
            f"or run `ant auth login`. ({e})"
        ) from e

    prompt = _build_prompt(baseline, bypasses)

    # Stream (adaptive thinking can lengthen the turn) and take the final
    # message. max_tokens is generous because adaptive thinking tokens count
    # toward it — too low and the structured JSON gets cut off mid-object.
    try:
        with client.messages.stream(
            model=model,
            max_tokens=16000,
            system=_SYSTEM,
            thinking={"type": "adaptive"},
            output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
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
        raise RuntimeError("The model declined to analyze this request.")
    if message.stop_reason == "max_tokens":
        raise RuntimeError(
            "The AI response was cut off before it finished (hit the token limit). "
            "Try again, or reduce the number of bypasses analysed at once."
        )

    text = next((b.text for b in message.content if b.type == "text"), "")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Could not parse AI response as JSON: {e}") from e
