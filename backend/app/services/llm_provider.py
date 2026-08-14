import os

import httpx

from ..ai.prompts.system_prompt import SYSTEM_PROMPT


class UTservioLLMProvider:
    def __init__(self):
        self.api_key = os.environ.get("LLM_API_KEY")
        if not self.api_key:
            raise ValueError("LLM_API_KEY environment variable is not set")
        self.base_url = "https://llm-proxy.utservio.workers.dev/api/llm"

    async def generate_response(
        self,
        user_message: str,
        history: list | None = None,
        system_prompt: str | None = None,
    ) -> str:
        # Build prompt string
        sys_prompt = system_prompt or SYSTEM_PROMPT
        prompt_string = f"System Instructions: {sys_prompt}\n"
        if history:
            for msg in history:
                prompt_string += f"{msg['role'].capitalize()}: {msg['content']}\n"

        prompt_string += f"User: {user_message}\nAssistant: "

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload = {"input": prompt_string}

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    self.base_url, headers=headers, json=payload
                )
                response.raise_for_status()
                data = response.json()

                # Extract text exactly as frontend expected
                output_arr = data.get("output", [])
                message_obj = next(
                    (o for o in output_arr if o.get("type") == "message"), None
                )
                if message_obj and message_obj.get("content"):
                    return message_obj["content"][0].get("text", "")

                raise ValueError("Invalid response structure from LLM provider")

            except httpx.TimeoutException as e:
                raise RuntimeError("LLM Provider timeout") from e
            except httpx.HTTPStatusError as e:
                raise RuntimeError(
                    f"LLM Provider error: {e.response.status_code}"
                ) from e
            except Exception as e:
                raise RuntimeError(
                    f"Failed to communicate with LLM Provider: {e!s}"
                ) from e
