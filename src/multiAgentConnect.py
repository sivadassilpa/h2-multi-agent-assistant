"""Route chat requests to the right Azure AI Agent."""

import asyncio
import json

from azure.ai.projects import AIProjectClient
from azure.identity.aio import DefaultAzureCredential
from openai import AsyncAzureOpenAI
from semantic_kernel.agents import AzureAIAgent, AzureAIAgentThread

from .config import get_optional_env, get_required_env


user_queries: list[str] = []


def create_openai_client() -> AsyncAzureOpenAI:
    return AsyncAzureOpenAI(
        api_key=get_required_env("AZURE_OPENAI_API_KEY"),
        azure_endpoint=get_required_env("AZURE_OPENAI_ENDPOINT"),
        api_version=get_required_env("AZURE_OPENAI_API_VERSION"),
    )


async def detect_intent(user_input: str) -> tuple[str, str | None]:
    prompt = f"""
    You are an AI assistant that classifies user queries.

    Classify the user's intent into one of the following:
    - "projects": for queries related to finding hydrogen producers, consumers, storage, or projects.
    - "knowledge": for queries asking about H2Digital's platform or features.
    - "email": for queries that involve contacting a specific project via email.

    Return JSON with two keys:
    - "intent": one of "projects", "knowledge", or "email".
    - "project": the project name for email requests, otherwise null.

    Query: "{user_input}"
    Return JSON only, like: {{"intent": "projects", "project": null}}
    """

    client = create_openai_client()
    try:
        response = await client.chat.completions.create(
            model=get_required_env("AZURE_OPENAI_DEPLOYMENT_NAME"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
    finally:
        await client.close()

    content = response.choices[0].message.content.strip()
    try:
        result = json.loads(content)
        return result["intent"], result.get("project")
    except Exception as exc:
        print("Failed to parse intent response:", exc, "| Raw:", content)
        return "unknown", None


async def handle_multi_agent_query(user_query: str) -> str:
    global user_queries

    project_connection_string = get_required_env("AZURE_AI_PROJECT_CONNECTION_STRING")
    knowledge_agent_id = get_required_env("AZURE_AI_KNOWLEDGE_AGENT_ID")
    projects_agent_id = get_required_env("AZURE_AI_PROJECTS_AGENT_ID")
    email_agent_id = get_required_env("AZURE_AI_EMAIL_AGENT_ID")
    configured_thread_id = get_optional_env("AZURE_AI_AGENT_THREAD_ID")

    async with (
        DefaultAzureCredential() as creds,
        AzureAIAgent.create_client(credential=creds) as client,
    ):
        try:
            AIProjectClient.from_connection_string(
                conn_str=project_connection_string,
                credential=creds,
            )
            print("Project client initialized.")
        except Exception as exc:
            print(f"Error initializing project client: {exc}")
            return "Error: Azure AI project client initialization failed."

        knowledge_agent_definition = await client.agents.get_agent(
            agent_id=knowledge_agent_id
        )
        projects_agent_definition = await client.agents.get_agent(
            agent_id=projects_agent_id
        )
        email_agent_definition = await client.agents.get_agent(agent_id=email_agent_id)

        knowledge_agent = AzureAIAgent(
            client=client,
            definition=knowledge_agent_definition,
        )
        projects_agent = AzureAIAgent(client=client, definition=projects_agent_definition)
        email_agent = AzureAIAgent(client=client, definition=email_agent_definition)

        if user_query == "INIT":
            user_queries = [
                "Welcome the user with a simple hydrogen industry joke that a child could understand."
            ]
            agent = knowledge_agent
        else:
            intent, _project_name = await detect_intent(user_query)
            print(f"Routing intent '{intent}' for query: {user_query}")

            if intent == "knowledge":
                agent = knowledge_agent
            elif intent == "projects":
                agent = projects_agent
            elif intent == "email":
                agent = email_agent
            else:
                return "Sorry, I could not determine which agent should handle that request."

            user_queries = user_queries + [user_query]

        thread = AzureAIAgentThread(client=client, thread_id=configured_thread_id)
        response = await agent.get_response(messages=user_queries, thread=thread)
        print("Response:", response)

        if not configured_thread_id and response.thread:
            try:
                await response.thread.delete()
            except Exception as exc:
                print(f"Error deleting temporary thread {response.thread.id}: {exc}")

    reply_text = (
        response.message.content if response.message else "No response from agent."
    )
    user_queries = user_queries + [reply_text]
    return reply_text


async def handle_query(message: str) -> str:
    return await handle_multi_agent_query(message)


if __name__ == "__main__":
    asyncio.run(handle_multi_agent_query("What is H2Digital?"))
