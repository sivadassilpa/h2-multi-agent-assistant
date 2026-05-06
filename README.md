# H2 Multi-Agent Assistant

A FastAPI backend that routes hydrogen-industry questions to specialized Azure AI Agents. The app can answer H2Digital knowledge questions, search hydrogen projects through Azure AI Search, and route contact/email-style requests to a dedicated agent.

## What It Demonstrates

- Multi-agent orchestration with Azure AI Agents and Semantic Kernel
- Intent detection with Azure OpenAI
- Tool/function calling through a Semantic Kernel search plugin
- Azure AI Search integration for project discovery
- A small FastAPI API surface that can be connected to a web or avatar frontend

## Architecture

```text
User / Frontend
  -> FastAPI
    -> Intent detector, Azure OpenAI
      -> Knowledge agent
      -> Project search agent
      -> Email/contact agent
    -> Azure AI Search project lookup
```

## API

`POST /chat/conversations`

Routes a user message to the right Azure AI Agent.

```json
{
  "message": "Find hydrogen producers near Mannheim"
}
```

`POST /chat/findProjects`

Runs the project search flow and returns matched project IDs plus a readable summary.

```json
{
  "message": "Show me 3 active hydrogen consumers in Bavaria"
}
```

## Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create your local environment file:

```powershell
Copy-Item .env.example .env
```

Fill in the values in `.env`:

```text
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_VERSION=
AZURE_OPENAI_DEPLOYMENT_NAME=
AZURE_AI_PROJECT_CONNECTION_STRING=
AZURE_AI_KNOWLEDGE_AGENT_ID=
AZURE_AI_PROJECTS_AGENT_ID=
AZURE_AI_EMAIL_AGENT_ID=
AZURE_SEARCH_ENDPOINT=
AZURE_SEARCH_API_KEY=
AZURE_SEARCH_INDEX=
```

Sign in to Azure if you use `DefaultAzureCredential` locally:

```powershell
az login
```

Run the API from the project root:

```powershell
uvicorn src.server:app --reload
```

Open the interactive docs at:

```text
http://127.0.0.1:8000/docs
```

You can also check that the API is alive at:

```text
http://127.0.0.1:8000/health
```

## Project Structure

```text
src/
  server.py              FastAPI app and API routes
  multiAgentConnect.py   Intent routing and Azure AI Agent orchestration
  findProjects.py        Semantic Kernel project search plugin
  config.py              Environment variable helpers
```

Local trial scripts, virtual environments, caches, and secrets are ignored so the GitHub repo stays focused on the working app.

## Security

Do not commit `.env` or real Azure keys. This repo includes `.env.example` for configuration names only. If a key was ever hardcoded while experimenting, rotate it before publishing the project.
