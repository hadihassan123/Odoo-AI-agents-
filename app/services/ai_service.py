import json
from typing import Any

import requests
from requests import Response

from app.core.config import settings
from app.utils.retry import retry_request


class AIServiceError(Exception):
    pass


class AIStudioService:
    def __init__(self):
        self.timeout = settings.request_timeout
        self.retries = settings.request_retries
        self.retry_delay = settings.retry_delay_seconds

    def generate_response(
        self,
        message: str,
        provider: str = "groq",
        mode: str = "general",
        history: list[dict[str, str]] | None = None,
        context: str | None = None,
    ) -> str:
        history = history or []
        messages = self._build_messages(message=message, mode=mode, history=history, context=context)

        if mode == "pipeline":
            return self._run_pipeline(messages, provider)

        return self._call_provider(provider, messages)

    def _build_messages(
        self,
        message: str,
        mode: str,
        history: list[dict[str, str]],
        context: str | None,
    ) -> list[dict[str, str]]:
        system_prompt = self._build_system_prompt(mode=mode, context=context)
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": message})
        return messages

    def _build_system_prompt(self, mode: str, context: str | None) -> str:
        base_prompts = {
            "general": "You are a general-purpose AI assistant. Be accurate, concise, and practical.",
            "pipeline": "You are a senior software engineer. Produce implementation-ready code and explain tradeoffs briefly.",
            "knowledge": "You answer questions using the provided context when it is relevant. Say when context is missing.",
        }
        prompt = base_prompts.get(mode, base_prompts["general"])
        if context:
            prompt = f"{prompt}\n\nContext:\n{context}"
        return prompt

    def _run_pipeline(self, messages: list[dict[str, str]], provider: str) -> str:
        draft = self._call_provider(provider, messages)
        review_messages = [
            {"role": "system", "content": "You are a strict code reviewer. Identify correctness issues, risks, and missing tests."},
            {"role": "user", "content": f"Review this draft:\n\n{draft}"},
        ]
        review = self._call_provider("gemma" if provider == "groq" else provider, review_messages)
        fix_messages = messages + [
            {"role": "assistant", "content": draft},
            {"role": "user", "content": f"Review feedback:\n\n{review}\n\nRevise the draft accordingly."},
        ]
        return self._call_provider(provider, fix_messages)

    def _call_provider(self, provider: str, messages: list[dict[str, str]]) -> str:
        if provider == "groq":
            return retry_request(
                lambda: self._post_chat_completion(
                    url="https://api.groq.com/openai/v1/chat/completions",
                    api_key=settings.groq_api_key,
                    model=settings.groq_model,
                    messages=messages,
                ),
                retries=self.retries,
                delay=self.retry_delay,
            )
        if provider == "gemma":
            return retry_request(
                lambda: self._post_chat_completion(
                    url="https://openrouter.ai/api/v1/chat/completions",
                    api_key=settings.openrouter_api_key,
                    model=settings.openrouter_model,
                    messages=messages,
                ),
                retries=self.retries,
                delay=self.retry_delay,
            )
        raise AIServiceError(f"Unsupported provider: {provider}")

    def _post_chat_completion(
        self,
        url: str,
        api_key: str,
        model: str,
        messages: list[dict[str, str]],
    ) -> str:
        if not api_key:
            raise AIServiceError(f"Missing API key for provider request to {url}")

        try:
            response = requests.post(
                url,
                headers=self._build_headers(url=url, api_key=api_key),
                json={
                    "model": model,
                    "messages": messages,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise self._format_request_error(exc) from exc

        payload = self._parse_payload(response)
        try:
            return payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIServiceError(f"Unexpected provider response: {json.dumps(payload)}") from exc

    def _build_headers(self, url: str, api_key: str) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if "openrouter.ai" in url:
            headers["HTTP-Referer"] = "http://localhost"
            headers["X-Title"] = settings.app_name
        return headers

    def _parse_payload(self, response: Response) -> dict[str, Any]:
        try:
            return response.json()
        except ValueError as exc:
            raise AIServiceError(f"Provider returned non-JSON response: {response.text}") from exc

    def _format_request_error(self, exc: requests.RequestException) -> AIServiceError:
        response = getattr(exc, "response", None)
        if response is None:
            return AIServiceError(f"Provider request failed: {exc}")

        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        return AIServiceError(f"Provider request failed with status {response.status_code}: {detail}")


ai_studio_service = AIStudioService()
