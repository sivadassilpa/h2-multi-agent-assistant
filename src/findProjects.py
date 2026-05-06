"""Project search agent powered by Semantic Kernel and Azure AI Search."""

import asyncio
import json
from typing import Annotated

import requests
from semantic_kernel import Kernel
from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread
from semantic_kernel.connectors.ai import FunctionChoiceBehavior
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.functions import KernelArguments, kernel_function

from .config import get_required_env


class ProjectSearchPlugin:
    @kernel_function(description="Search projects by filters and/or query string")
    def search_projects(
        self,
        query: Annotated[
            str, "Freeform search text like project name or description"
        ] = "",
        filters: Annotated[str, "Filter expression for Azure Search"] = "",
        order_by: Annotated[str, "Order by field"] = "",
        top: Annotated[int, "Number of records to return"] = 10,
    ) -> Annotated[str, "List of matched projects"]:

        endpoint = get_required_env("AZURE_SEARCH_ENDPOINT")
        index_name = get_required_env("AZURE_SEARCH_INDEX")
        api_key = get_required_env("AZURE_SEARCH_API_KEY")
        url = f"{endpoint}/indexes/{index_name}/docs/search?api-version=2023-07-01-Preview"

        headers = {"Content-Type": "application/json", "api-key": api_key}

        body = {
            "search": query or "*",
            "filter": filters if filters else None,
            "orderby": order_by if order_by else None,
            "top": top,
        }

        body = {k: v for k, v in body.items() if v is not None}

        response = requests.post(url, json=body, headers=headers, timeout=20)
        response.raise_for_status()
        results = response.json()
        projects = results.get("value", [])
        if not projects:
            return json.dumps(
                {
                    "action": "search",
                    "content": {
                        "message": "No projects found matching your criteria.",
                        "idList": [],
                    },
                }
            )

        content_lines = [
            f"- {p.get('LocationName', 'Unnamed')} [ID: {p.get('ProjectId', 'N/A')}]: {p.get('Description', '')}"
            for p in projects
        ]
        project_ids = [p.get("LocationId") for p in projects if "LocationId" in p]

        return json.dumps(
            {
                "action": "search",
                "content": {"message": "\n".join(content_lines), "idList": project_ids},
            }
        )


user_queries = []


async def findProjects(message: str):
    global user_queries
    service_id = "agent"
    kernel = Kernel()
    kernel.add_plugin(ProjectSearchPlugin(), plugin_name="projects")
    kernel.add_service(
        AzureChatCompletion(
            deployment_name=get_required_env("AZURE_OPENAI_DEPLOYMENT_NAME"),
            service_id=service_id,
        )
    )
    settings = kernel.get_prompt_execution_settings_from_service_id(
        service_id=service_id
    )
    settings.function_choice_behavior = FunctionChoiceBehavior.Auto()
    agent = ChatCompletionAgent(
        kernel=kernel,
        name="Host",
        instructions=(
            "You are a backend system agent. Always call the function 'projects.search_projects'. "
            "If projects.search_projects returns projects, respond only with the raw JSON output "
            "from the function. Do not add extra text."
        ),
        arguments=KernelArguments(settings=settings),
    )

    thread: ChatHistoryAgentThread | None = None
    user_queries = user_queries + [message]

    try:
        async for response in agent.invoke(messages=user_queries, thread=thread):
            print(f"# {response.name}: {response}")
            thread = response.thread
            try:
                response_content = str(response.message.content)
                parsed = json.loads(response_content)
                content_data = parsed.get("content", {})

                return {
                    "message": content_data.get("message", ""),
                    "action": parsed.get("action", ""),
                    "data": {"projectIdList": content_data.get("idList", [])},
                }

            except (json.JSONDecodeError, AttributeError, TypeError):
                return {
                    "message": str(response.message.content),
                    "action": "unknown",
                    "data": {"projectIdList": []},
                }
    finally:
        if thread:
            await thread.delete()

    return {
        "message": "No response from project search agent.",
        "action": "unknown",
        "data": {"projectIdList": []},
    }


async def handle_find_projects(message: str):
    return await findProjects(message)


if __name__ == "__main__":
    asyncio.run(findProjects("Find hydrogen projects near Mannheim"))
