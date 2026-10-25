"""LLM access (Gemini / Groq over REST) plus graceful demo-mode fallback."""
from __future__ import annotations

import os
from dataclasses import dataclass

import requests
from fastapi import Header

from .core import img_to_b64, parse_json

DEFAULT_MODELS = {"Gemini": "gemini-2.5-flash", "Groq": "meta-llama/llama-4-scout-17b-16e-instruct"}


@dataclass
class LLMConfig:
    provider: str
    api_key: str
    model: str
    demo: bool

    @property
    def live(self) -> bool:
        return bool(self.api_key) and not self.demo


def get_config(
    x_api_key: str | None = Header(default=None),
    x_provider: str | None = Header(default=None),
    x_model: str | None = Header(default=None),
    x_demo_mode: str | None = Header(default=None),
) -> LLMConfig:
    """Per-request AI settings. Keys come from the browser header or server env; never stored."""
    provider = x_provider if x_provider in DEFAULT_MODELS else os.getenv("LLM_PROVIDER", "Gemini")
    if provider not in DEFAULT_MODELS:
        provider = "Gemini"
    env_key = os.getenv("GEMINI_API_KEY" if provider == "Gemini" else "GROQ_API_KEY", "")
    return LLMConfig(
        provider=provider,
        api_key=(x_api_key or env_key or "").strip(),
        model=(x_model or DEFAULT_MODELS[provider]).strip(),
        demo=(x_demo_mode == "1"),
    )


def call_llm(cfg: LLMConfig, prompt: str, images: list | None = None) -> dict:
    images = (images or [])[:4]
    if cfg.provider == "Gemini":
        parts = [{"text": prompt}] + [
            {"inline_data": {"mime_type": "image/jpeg", "data": img_to_b64(im)}} for im in images
        ]
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{cfg.model}:generateContent",
            headers={"x-goog-api-key": cfg.api_key, "Content-Type": "application/json"},
            json={
                "contents": [{"parts": parts}],
                "generationConfig": {"temperature": 0.3, "responseMimeType": "application/json"},
            },
            timeout=90,
        )
        r.raise_for_status()
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
    else:
        content = [{"type": "text", "text": prompt}] + [
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + img_to_b64(im)}}
            for im in images
        ]
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {cfg.api_key}", "Content-Type": "application/json"},
            json={"model": cfg.model, "messages": [{"role": "user", "content": content}], "temperature": 0.3},
            timeout=90,
        )
        r.raise_for_status()
        text = r.json()["choices"][0]["message"]["content"]
    return parse_json(text)


def run_with_fallback(cfg: LLMConfig, live_fn, demo_fn) -> dict:
    """Try the live model; on any failure return demo output plus a `warning`."""
    warning = None
    if cfg.live:
        try:
            res = live_fn()
            res["_source"] = "live"
            return res
        except requests.HTTPError as e:
            code = e.response.status_code if e.response is not None else "?"
            warning = f"AI provider error (HTTP {code}). Check your API key and model name. Showing demo result."
        except Exception as e:  # noqa: BLE001
            warning = f"Live analysis failed ({type(e).__name__}). Showing demo result."
    res = demo_fn()
    res["_source"] = "demo"
    if warning:
        res["warning"] = warning
    return res
