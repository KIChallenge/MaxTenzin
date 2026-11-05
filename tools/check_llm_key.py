"""Quick check whether an Azure AI Foundry key works.

Usage (from repo root):
    services/api/.venv/bin/python tools/check_llm_key.py            # key + endpoint from .env
    services/api/.venv/bin/python tools/check_llm_key.py --prompt   # paste a key (hidden input)
    services/api/.venv/bin/python tools/check_llm_key.py --prompt --endpoint https://<account>.services.ai.azure.com/openai/v1

Exit code 0 = key works, 1 = rejected / error.
"""

import argparse
import sys
from getpass import getpass
from pathlib import Path

import openai
from dotenv import dotenv_values

env = dotenv_values(Path(__file__).resolve().parents[1] / ".env")

p = argparse.ArgumentParser()
p.add_argument("--prompt", action="store_true", help="ask for the key instead of using .env")
p.add_argument("--endpoint", default=env.get("AZURE_ENDPOINT_URL", ""))
p.add_argument("--model", default=env.get("LLM_MODEL", "gpt-5-4-mini"))
a = p.parse_args()

key = getpass("API key: ") if a.prompt else env.get("AZURE_API_KEY", "")
key = (key or "").strip().strip("\"'")
endpoint = a.endpoint.rstrip("/")

print("Endpoint:", endpoint or "MISSING")
print("Model:   ", a.model)
print("Key:     ", f"{len(key)} chars, {key[:4]}…{key[-4:]}" if key else "MISSING")
if not key or not endpoint:
    sys.exit(1)

try:
    r = openai.OpenAI(base_url=endpoint, api_key=key).chat.completions.create(
        model=a.model,
        messages=[{"role": "user", "content": "Antworte nur mit: ok"}],
        max_completion_tokens=50,
    )
    print("✅ Key works. Reply:", r.choices[0].message.content)
    sys.exit(0)
except openai.AuthenticationError as e:
    print("❌ 401: key invalid for this endpoint (wrong/rotated key or key from another resource)\n", e)
except openai.NotFoundError as e:
    print(f"❌ 404: endpoint path or model/deployment '{a.model}' not found\n", e)
except openai.RateLimitError as e:
    print("⚠️  429: key works, but rate-limited / quota exhausted\n", e)
    sys.exit(0)
except openai.APIConnectionError as e:
    print("❌ Network error (DNS/TLS/proxy?)\n", e)
sys.exit(1)
