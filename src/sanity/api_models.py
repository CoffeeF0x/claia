"""Sanity: ping every hosted API catalog model.

Run after catalog or architecture updates, or whenever you want to
confirm the configured keys still work:

  PYTHONPATH=src python -m sanity.api_models
  PYTHONPATH=src python -m sanity.api_models --only openai
  PYTHONPATH=src python -m sanity.api_models gpt-4o-mini haiku

Tokens come from the environment (OPENAI_API_TOKEN, ANTHROPIC_API_TOKEN,
OPENROUTER_API_TOKEN, with optional CLAIA_ prefix or provider-native
names). Access-tier and rate-limit misses print as skip, not fail.
"""

from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from claia.core.enums.conversation import MessageRole
from claia.core.results import DeploymentError, ResolveError
from claia.framework import Conversation, Registry


########################################################################
#                              CONSTANTS                               #
########################################################################
API_ARCHITECTURES = ("openai", "anthropic", "openrouter")
PROMPT = "Reply with the single word pong."
GENERATE_ARGS = {
  "stream": False,
  "max_tokens": 1024,
  "effort": "low",
}

TRANSIENT_MARKERS = (
  "429",
  "too many requests",
  "rate limit",
  "503",
  "overloaded",
  "temporarily",
)

ACCESS_MARKERS = (
  "access",
  "permission",
  "not authorized",
  "not_authorized",
  "quota",
  "credit",
  "billing",
  "insufficient",
  "not available",
  "invalid_api_key",
  "incorrect api key",
  "401",
  "402",
  "403",
)

TOKEN_ENV = {
  "openai_api_token": (
    "CLAIA_OPENAI_API_TOKEN", "OPENAI_API_TOKEN", "OPENAI_API_KEY",
  ),
  "anthropic_api_token": (
    "CLAIA_ANTHROPIC_API_TOKEN", "ANTHROPIC_API_TOKEN", "ANTHROPIC_API_KEY",
  ),
  "openrouter_api_token": (
    "CLAIA_OPENROUTER_API_TOKEN", "OPENROUTER_API_TOKEN", "OPENROUTER_API_KEY",
  ),
}


########################################################################
#                               HELPERS                                #
########################################################################
def _load_env():
  load_dotenv()
  here = Path(__file__).resolve()
  for candidate in (
    here.parents[2] / ".env",
    Path("/workspaces/claia/.env"),
    Path("/workspaces/slate/.env"),
  ):
    if candidate.is_file():
      load_dotenv(candidate, override=False)


def _token(*names):
  for name in names:
    value = os.environ.get(name)
    if not value:
      continue
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
      value = value[1:-1].strip()
    if value:
      return value
  return None


def _plugin_kwargs():
  kwargs = {}
  for key, names in TOKEN_ENV.items():
    value = _token(*names)
    if value:
      kwargs[key] = value
  referer = _token("CLAIA_OPENROUTER_HTTP_REFERER", "OPENROUTER_HTTP_REFERER")
  title = _token("CLAIA_OPENROUTER_X_TITLE", "OPENROUTER_X_TITLE")
  if referer:
    kwargs["openrouter_http_referer"] = referer
  if title:
    kwargs["openrouter_x_title"] = title
  return kwargs


def _is_api_model(definition) -> bool:
  architectures = getattr(definition, "architectures", None) or []
  return any(name in API_ARCHITECTURES for name in architectures)


def _is_access_error(message: str) -> bool:
  lowered = message.lower()
  return any(marker in lowered for marker in ACCESS_MARKERS)


def _is_transient_error(message: str) -> bool:
  lowered = message.lower()
  return any(marker in lowered for marker in TRANSIENT_MARKERS)


def _parse_args(argv):
  only = None
  names = []
  args = list(argv)
  if "--only" in args:
    idx = args.index("--only")
    args.pop(idx)
    if not args:
      raise SystemExit("usage: python -m sanity.api_models [--only company] [model ...]")
    only = args.pop(idx).lower()
  names = args
  return only, names


def _select_models(catalog, only, names):
  selected = []
  for name, definition in catalog.items():
    if not _is_api_model(definition):
      continue
    company = (getattr(definition, "company", None) or "").lower()
    if only and only not in company and only not in (getattr(definition, "architectures", None) or []):
      continue
    selected.append((name, definition))

  if names:
    wanted = set(names)
    resolved = []
    for name, definition in selected:
      aliases = getattr(definition, "aliases", None) or []
      if name in wanted or any(alias in wanted for alias in aliases):
        resolved.append((name, definition))
        wanted -= {name, *(aliases or [])}
    if wanted:
      print(f"unknown model filter(s): {', '.join(sorted(wanted))}")
    return resolved
  return selected


def _redact(message: str) -> str:
  """Drop credential-shaped spans from provider error text."""
  return re.sub(r'(sk-[A-Za-z0-9_\-]+|Bearer\s+\S+)', '[redacted]', message)


def _preview(text: str) -> str:
  compact = " ".join((text or "").split())
  return compact[:80] + ("..." if len(compact) > 80 else "")


########################################################################
#                                 RUN                                  #
########################################################################
def ping(registry, model_name: str, attempts: int = 3):
  conversation = Conversation(title=f"sanity-{model_name}")
  conversation.add_message(MessageRole.USER, PROMPT)
  last_error = None
  for attempt in range(1, attempts + 1):
    started = time.monotonic()
    try:
      response = registry.run(model_name, conversation, **GENERATE_ARGS)
      elapsed = time.monotonic() - started
      if not response.is_success():
        raise DeploymentError(str(response.error) or "generate failed")
      text = response.text().strip()
      if not text:
        raise DeploymentError("empty response")
      return text, elapsed, response.usage
    except Exception as exc:
      last_error = exc
      if attempt < attempts and _is_transient_error(str(exc)):
        time.sleep(2 * attempt)
        continue
      raise
  raise last_error


def main(argv=None):
  _load_env()
  only, names = _parse_args(argv if argv is not None else sys.argv[1:])
  kwargs = _plugin_kwargs()
  if not kwargs:
    print("No API tokens in the environment. Set OPENAI_API_TOKEN,")
    print("ANTHROPIC_API_TOKEN, and/or OPENROUTER_API_TOKEN.")
    return 2

  print("keys:", ", ".join(f"{k}({len(v)})" for k, v in sorted(kwargs.items())))
  registry = Registry()
  registry.load_plugins(**kwargs)
  catalog = registry.get_supported_models()
  selected = _select_models(catalog, only, names)
  print(f"models: {len(selected)}")
  print()

  ok = skip = fail = 0
  for name, definition in selected:
    title = getattr(definition, "title", None) or name
    label = f"{name:28} {title}"
    try:
      text, elapsed, usage = ping(registry, name)
    except ResolveError as exc:
      skip += 1
      print(f"SKIP  {label}  ({exc})")
      continue
    except Exception as exc:
      message = str(exc)
      if _is_access_error(message):
        skip += 1
        print(f"SKIP  {label}  (access: {_redact(message)[:160]})")
      elif _is_transient_error(message):
        skip += 1
        print(f"SKIP  {label}  (transient: {_redact(message)[:160]})")
      else:
        fail += 1
        print(f"FAIL  {label}  ({_redact(message)[:200]})")
      continue

    tokens = ""
    if usage and usage.total_tokens is not None:
      tokens = f"  tokens={usage.total_tokens}"
    print(f"OK    {label}  {elapsed:.1f}s{tokens}  {_preview(text)}")
    ok += 1

  print()
  print(f"ok={ok}  skip={skip}  fail={fail}")
  return 1 if fail else 0


if __name__ == "__main__":
  raise SystemExit(main())
