"""
llm.py
------
Provider layer: Gemini first, Groq as fallback.

WHY THIS ORDER (it is not arbitrary - check the free-tier math):

  Gemini free tier   ~1,500 requests/day, very high token/minute ceiling.
                     Binding constraint is REQUESTS PER MINUTE (~10 on the
                     current free Flash models). Easy to work around by
                     batching more items per call.

  Groq free tier     30 requests/minute sounds better, but the binding
                     constraint is TOKENS PER DAY - on the order of
                     100K TPD for the 70B model. At roughly 10K tokens
                     per batch, that is ~10-20 batches before you are cut
                     off for the day.

So Gemini is your workhorse and Groq is a genuine failover for when
Gemini returns 429 or errors - not a co-equal second source. Do not
plan to run your whole corpus through Groq.

VERIFY MODEL NAMES BEFORE YOUR FIRST FULL RUN:
    python scripts/llm.py --list-models
Model identifiers change. That command asks each provider what it
actually offers on your key, so you are never guessing.

SETUP:
  Gemini (free, no card in supported regions):
    aistudio.google.com -> Get API key -> Create API key in new project
    Add to .env:  GEMINI_API_KEY=...

  Groq (free, no card):
    console.groq.com -> API Keys
    Add to .env:  GROQ_API_KEY=...
"""

import json
import os
import time

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------
# Model identifiers. Run --list-models and correct these if needed.
# ---------------------------------------------------------------
GEMINI_MODEL = "gemini-2.5-flash"
GROQ_MODEL = "llama-3.3-70b-versatile"

# Gemini free tier is request-per-minute limited. 7s between calls
# keeps us under ~10 RPM with margin.
GEMINI_MIN_INTERVAL = 7.0

# Groq is tokens-per-day limited, so pace is less useful than
# simply not leaning on it.
GROQ_MIN_INTERVAL = 2.5


class ProviderError(Exception):
    """Raised when a provider cannot fulfil a request."""


# ---------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------
class GeminiProvider:
    name = "gemini"

    def __init__(self):
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            raise ProviderError("GEMINI_API_KEY not set")

        try:
            # NOTE: the modern SDK is google-genai.
            # The old google-generativeai package was deprecated in
            # November 2025 - if a tutorial tells you to install that,
            # it is out of date.
            from google import genai
        except ImportError:
            raise ProviderError(
                "google-genai not installed. Run: pip install google-genai"
            )

        self.client = genai.Client(api_key=key)
        self._last_call = 0.0

    def _throttle(self):
        elapsed = time.time() - self._last_call
        if elapsed < GEMINI_MIN_INTERVAL:
            time.sleep(GEMINI_MIN_INTERVAL - elapsed)
        self._last_call = time.time()

    def complete(self, system_prompt, user_prompt, max_tokens=8000, json_mode=True):
        self._throttle()
        try:
            from google.genai import types

            config_args = {
                "system_instruction": system_prompt,
                "max_output_tokens": max_tokens,
                "temperature": 0,
            }
            if json_mode:
                config_args["response_mime_type"] = "application/json"

            resp = self.client.models.generate_content(
                model=GEMINI_MODEL,
                contents=user_prompt,
                config=types.GenerateContentConfig(**config_args),
            )
            return resp.text
        except Exception as e:
            raise ProviderError(f"gemini: {e}")

    def list_models(self):
        return [m.name for m in self.client.models.list()]


# ---------------------------------------------------------------
# Groq
# ---------------------------------------------------------------
class GroqProvider:
    name = "groq"

    def __init__(self):
        key = os.getenv("GROQ_API_KEY")
        if not key:
            raise ProviderError("GROQ_API_KEY not set")

        try:
            from groq import Groq
        except ImportError:
            raise ProviderError("groq not installed. Run: pip install groq")

        self.client = Groq(api_key=key)
        self._last_call = 0.0

    def _throttle(self):
        elapsed = time.time() - self._last_call
        if elapsed < GROQ_MIN_INTERVAL:
            time.sleep(GROQ_MIN_INTERVAL - elapsed)
        self._last_call = time.time()

    def complete(self, system_prompt, user_prompt, max_tokens=8000, json_mode=True):
        self._throttle()
        try:
            kwargs = {
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": 0,
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            resp = self.client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content
        except Exception as e:
            raise ProviderError(f"groq: {e}")

    def list_models(self):
        return [m.id for m in self.client.models.list().data]


# ---------------------------------------------------------------
# Router: Gemini first, Groq on failure
# ---------------------------------------------------------------
class LLMRouter:
    """
    Tries Gemini. On failure, falls back to Groq for that call only -
    it does NOT permanently switch, because Gemini failures are usually
    transient rate limits that clear within the minute.

    Tracks which provider served each call so you can report the split
    in your methodology slide.
    """

    def __init__(self, verbose=True):
        self.verbose = verbose
        self.providers = []
        self.stats = {"gemini": 0, "groq": 0, "failed": 0}

        for cls in (GeminiProvider, GroqProvider):
            try:
                self.providers.append(cls())
                if verbose:
                    print(f"  [ok] {cls.name} ready")
            except ProviderError as e:
                if verbose:
                    print(f"  [--] {cls.name} unavailable: {e}")

        if not self.providers:
            raise SystemExit(
                "\nNo LLM provider available.\n"
                "Set GEMINI_API_KEY (preferred) or GROQ_API_KEY in .env\n"
                "  Gemini: aistudio.google.com\n"
                "  Groq:   console.groq.com\n"
            )

    def complete(self, system_prompt, user_prompt, max_tokens=8000, json_mode=True):
        errors = []

        for provider in self.providers:
            try:
                result = provider.complete(system_prompt, user_prompt, max_tokens, json_mode=json_mode)
                self.stats[provider.name] += 1
                return result, provider.name
            except ProviderError as e:
                errors.append(str(e))
                if self.verbose:
                    print(f"    ({provider.name} failed, trying next)")
                continue

        self.stats["failed"] += 1
        raise ProviderError(" | ".join(errors))

    def report(self):
        total = self.stats["gemini"] + self.stats["groq"]
        if not total:
            return "No successful calls."
        return (
            f"Calls served - gemini: {self.stats['gemini']} "
            f"({self.stats['gemini'] / total * 100:.0f}%), "
            f"groq: {self.stats['groq']} "
            f"({self.stats['groq'] / total * 100:.0f}%), "
            f"failed: {self.stats['failed']}"
        )


def parse_json_response(text):
    """
    Both providers are asked for JSON, but wrap defensively anyway.
    Handles: markdown fences, and objects-wrapping-arrays (Groq's
    json_object mode cannot return a bare array, so it often nests
    the list under a key).
    """
    t = (text or "").strip()

    if t.startswith("```"):
        parts = t.split("```")
        if len(parts) > 1:
            t = parts[1]
            if t.lstrip().startswith("json"):
                t = t.lstrip()[4:]
    t = t.strip()

    data = json.loads(t)

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        # find the first list-valued key
        for v in data.values():
            if isinstance(v, list):
                return v
        return [data]

    raise ValueError(f"Unexpected JSON shape: {type(data)}")


if __name__ == "__main__":
    import sys

    if "--list-models" in sys.argv:
        print("Checking what your keys can actually access...\n")
        for cls in (GeminiProvider, GroqProvider):
            try:
                p = cls()
                print(f"--- {cls.name} ---")
                for m in p.list_models():
                    print(f"  {m}")
                print()
            except Exception as e:
                print(f"--- {cls.name}: unavailable ({e}) ---\n")
        print("Set GEMINI_MODEL / GROQ_MODEL at the top of this file")
        print("to a name that appears above.")
    else:
        print("Testing providers...\n")
        router = LLMRouter()
        out, who = router.complete(
            "Reply with JSON only.",
            'Return {"status": "working"}',
            max_tokens=100,
        )
        print(f"\nServed by: {who}")
        print(f"Response: {out.strip()}")
