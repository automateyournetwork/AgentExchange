import asyncio
import os
import traceback
from uuid import uuid4
from typing import Any, Optional
from urllib.parse import urljoin, urlparse, parse_qs

import httpx
from dotenv import load_dotenv
from authlib.integrations.httpx_client import AsyncOAuth2Client

from a2a.client import A2AClient
from a2a.types import (
    SendMessageRequest,
    MessageSendParams,
    GetTaskRequest,
    TaskQueryParams,
    SendMessageSuccessResponse,
    TaskState,
)

# === Load env ===
load_dotenv()
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI", "https://localhost/auth")
AGENT_REGISTRY_URL = os.getenv("AGENT_REGISTRY_URL", "https://localhost:3000/agents/search")

# === OAuth ===
async def get_google_oauth_token() -> str:
    oauth_client = AsyncOAuth2Client(
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope='openid email profile',
    )
    authorization_url, _ = oauth_client.create_authorization_url(
        'https://accounts.google.com/o/oauth2/v2/auth'
    )
    print(f"🔗 Open this URL in your browser to authorize:\n{authorization_url}")
    redirect_response = input("🔑 Paste the full redirect URL here: ").strip()

    parsed = parse_qs(urlparse(redirect_response).query)
    code = parsed.get("code", [None])[0]
    if not code:
        error = parsed.get("error", [None])[0]
        desc = parsed.get("error_description", ["No description"])[0]
        raise ValueError(f"OAuth error: {error} - {desc}")

    token = await oauth_client.fetch_token(
        url='https://oauth2.googleapis.com/token',
        grant_type='authorization_code',
        code=code,
        redirect_uri=REDIRECT_URI,
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
    )
    return token["id_token"]

# === Chat message payload ===
def create_send_message_payload(text: str, task_id: str | None = None, context_id: str | None = None) -> dict[str, Any]:
    payload = {
        "message": {
            "role": "user",
            "parts": [{"kind": "text", "text": text}],
            "messageId": uuid4().hex,
        }
    }
    if task_id:
        payload["message"]["taskId"] = task_id
    if context_id:
        payload["message"]["contextId"] = context_id
    return payload

def extract_clean_text(task_data: dict[str, Any]) -> str:
    try:
        message_source = task_data.get("status", {}).get("message", {})
        if task_data.get("status", {}).get("state") == "completed" and task_data.get("result", {}).get("message"):
            message_source = task_data.get("result", {}).get("message", {})
        for part in message_source.get("parts", []):
            if "text" in part:
                return part["text"]
        return "[⚠️ No valid text found in message parts]"
    except Exception as e:
        return f"[⚠️ Error extracting text: {e}]"

# === Semantic Agent Lookup ===
async def find_best_agent(question: str, id_token: str) -> dict:
    headers = {"Authorization": f"Bearer {id_token}"}
    params = {"q": question}
    async with httpx.AsyncClient(headers=headers) as client:
        response = await client.get(AGENT_REGISTRY_URL, params=params)
        response.raise_for_status()
        agents = response.json().get("agents", [])
        if not agents:
            raise ValueError("❌ No agents matched your question.")
        best = agents[0]
        print(f"🤖 Selected agent: {best['name']} ({best['endpoint']})")
        return best

# === Chat loop ===
async def chat_loop(client: A2AClient, initial_prompt: Optional[str] = None):
    context_id = None
    task_id = None

    if initial_prompt:
        user_inputs = [initial_prompt]
    else:
        user_inputs = []

    while True:
        try:
            if not user_inputs:
                user_input = input("\n❓ Question: ").strip()
                if not user_input:
                    print("👋 Exiting.")
                    break
            else:
                user_input = user_inputs.pop(0)

            payload = create_send_message_payload(user_input, task_id, context_id)
            request = SendMessageRequest(params=MessageSendParams(**payload))

            print(f"🚀 Sending message to: {getattr(client, 'agent_endpoint', 'N/A')}")
            response_model = await client.send_message(request)

            if not isinstance(response_model, SendMessageSuccessResponse):
                print(f"❌ Failed to send message. Response: {response_model}")
                continue

            task = response_model.result
            task_id = task.id
            context_id = getattr(task, 'contextId', context_id)

            print(f"⏳ Task created: ID={task_id}, ContextID={context_id}. Polling for completion...")
            for i in range(60):
                await asyncio.sleep(1)
                task_response_model = await client.get_task(GetTaskRequest(params=TaskQueryParams(id=task_id)))
                task_status_data = task_response_model.result
                current_state = task_status_data.status.state
                print(f"📡 Status (Attempt {i+1}): {current_state}")

                if current_state == TaskState.completed:
                    answer = extract_clean_text(task_status_data.model_dump())
                    print(f"✅ Answer: {answer}")
                    break
                elif current_state in [TaskState.failed, TaskState.cancelled]:
                    error_message = extract_clean_text(task_status_data.model_dump())
                    print(f"❌ Task {current_state}: {error_message}")
                    break
            else:
                print(f"⚠️ Timeout waiting for response for task {task_id}.")

        except KeyboardInterrupt:
            print("\n👋 Conversation ended.")
            break
        except Exception as e:
            traceback.print_exc()
            print(f"❌ Unexpected error in chat loop: {e}")

# === Main entrypoint ===
async def main():
    try:
        print("🔐 Starting Google OAuth...")
        id_token_str = await get_google_oauth_token()
        print("✅ Authenticated.")

        question = input("💬 What do you want to ask? ").strip()
        if not question:
            raise ValueError("No question provided.")

        selected_agent = await find_best_agent(question, id_token_str)

        agent_card_url = urljoin(selected_agent["endpoint"], ".well-known/agent.json")
        async with httpx.AsyncClient(timeout=600.0) as http_client_session:
            card_resp = await http_client_session.get(agent_card_url)
            card_resp.raise_for_status()

            print("🛠️ Loading agent card and initializing A2AClient...")
            client = await A2AClient.get_client_from_agent_card_url(
                httpx_client=http_client_session,
                base_url=selected_agent["endpoint"],
                agent_card_path="/.well-known/agent.json"
            )
            await chat_loop(client, initial_prompt=question)

    except Exception as e:
        traceback.print_exc()
        print(f"❌ Fatal error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
