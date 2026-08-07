"""
Lab 11 — Helper Utilities
"""
import os
import requests
from google.genai import types


async def chat_with_agent(agent, runner, user_message: str, session_id=None):
    """Send a message to the agent and get the response.

    Args:
        agent: The LlmAgent instance
        runner: The InMemoryRunner instance
        user_message: Plain text message to send
        session_id: Optional session ID to continue a conversation

    Returns:
        Tuple of (response_text, session)
    """
    provider = os.environ.get("LLM_PROVIDER", "google").lower()

    if provider in ["openai", "gpt"]:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return "Error: OPENAI_API_KEY not found in environment.", None

        plugins = getattr(runner, "plugins", []) or []

        class DummyPart:
            def __init__(self, text):
                self.text = text

        class DummyContent:
            def __init__(self, text):
                self.parts = [DummyPart(text)]
                self.role = "user"

        # 1. Input plugins callback
        for plugin in plugins:
            if hasattr(plugin, "on_user_message_callback"):
                res = await plugin.on_user_message_callback(
                    invocation_context=None,
                    user_message=DummyContent(user_message),
                )
                if res and hasattr(res, "parts") and res.parts:
                    blocked_text = "".join(
                        p.text for p in res.parts if getattr(p, "text", None)
                    )
                    return blocked_text, None

        # 2. Call OpenAI (GPT)
        system_instruction = getattr(
            agent, "instruction", "You are a helpful assistant."
        )
        model_name = os.environ.get("LLM_MODEL_NAME", "gpt-4o-mini")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        temp = float(os.environ.get("LLM_TEMPERATURE", "0.0"))
        data = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_message},
            ],
            "temperature": temp,
        }

        try:
            import asyncio

            resp = await asyncio.to_thread(
                requests.post,
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30,
            )
            resp.raise_for_status()
            res_json = resp.json()
            reply_text = res_json["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"OpenAI API Error: {e}", None

        # 3. Output plugins callback
        for plugin in plugins:
            if hasattr(plugin, "after_model_callback"):
                class DummyLlmResponse:
                    def __init__(self, text):
                        self.content = DummyContent(text)

                dummy_resp = DummyLlmResponse(reply_text)
                mod_resp = await plugin.after_model_callback(
                    callback_context=None, llm_response=dummy_resp
                )
                if (
                    mod_resp
                    and hasattr(mod_resp, "content")
                    and mod_resp.content
                    and mod_resp.content.parts
                ):
                    reply_text = "".join(
                        p.text for p in mod_resp.content.parts if getattr(p, "text", None)
                    )

        return reply_text, None

    if provider == "deepseek":
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            return "Error: DEEPSEEK_API_KEY not found in environment.", None

        plugins = getattr(runner, "plugins", []) or []

        class DummyPart:
            def __init__(self, text):
                self.text = text

        class DummyContent:
            def __init__(self, text):
                self.parts = [DummyPart(text)]
                self.role = "user"

        # 1. Input plugins callback
        for plugin in plugins:
            if hasattr(plugin, "on_user_message_callback"):
                res = await plugin.on_user_message_callback(
                    invocation_context=None,
                    user_message=DummyContent(user_message),
                )
                if res and hasattr(res, "parts") and res.parts:
                    blocked_text = "".join(
                        p.text for p in res.parts if getattr(p, "text", None)
                    )
                    return blocked_text, None

        # 2. Call DeepSeek
        system_instruction = getattr(
            agent, "instruction", "You are a helpful assistant."
        )
        model_name = os.environ.get("LLM_MODEL_NAME", "deepseek-chat")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        temp = float(os.environ.get("LLM_TEMPERATURE", "0.0"))
        data = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.0,
        }

        try:
            import asyncio

            resp = await asyncio.to_thread(
                requests.post,
                "https://api.deepseek.com/chat/completions",
                headers=headers,
                json=data,
                timeout=30,
            )
            resp.raise_for_status()
            res_json = resp.json()
            reply_text = res_json["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"DeepSeek API Error: {e}", None

        # 3. Output plugins callback
        for plugin in plugins:
            if hasattr(plugin, "after_model_callback"):
                class DummyLlmResponse:
                    def __init__(self, text):
                        self.content = DummyContent(text)

                dummy_resp = DummyLlmResponse(reply_text)
                mod_resp = await plugin.after_model_callback(
                    callback_context=None, llm_response=dummy_resp
                )
                if (
                    mod_resp
                    and hasattr(mod_resp, "content")
                    and mod_resp.content
                    and mod_resp.content.parts
                ):
                    reply_text = "".join(
                        p.text for p in mod_resp.content.parts if getattr(p, "text", None)
                    )

        return reply_text, None

    user_id = "student"
    app_name = runner.app_name

    session = None
    if session_id is not None:
        try:
            session = await runner.session_service.get_session(
                app_name=app_name, user_id=user_id, session_id=session_id
            )
        except (ValueError, KeyError):
            pass

    if session is None:
        try:
            session = await runner.session_service.create_session(
                app_name=app_name, user_id=user_id
            )
        except Exception:
            session = await runner.session_service.create_session(
                app_name=app_name, user_id=user_id
            )

    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_message)],
    )

    final_response = ""
    async for event in runner.run_async(
        user_id=user_id, session_id=session.id, new_message=content
    ):
        if hasattr(event, "content") and event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    final_response += part.text

    return final_response, session
