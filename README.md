# Agentic AI et MCP — TP5

Agents IA avec LangChain et LangGraph, RAG agentique, serveur MCP et orchestration multi-agents.
LLM local : Ollama (qwen3:4b, qwen3:1.7b) · Embeddings : nomic-embed-text

## Progression
### A. LangChain
- [x] Étape 0 : Initialisation
- [X] Étape 1 : Agent simple + mémoire
- [X] Étape 2 : Tools personnalisés
- [X] Étape 3 : Tools prédéfinis (DuckDuckGo, Tavily, PythonREPL)
- [X] Étape 4 : Middlewares
- [X] Étape 5 : Chatbot RAG agentique

### B. LangGraph
- [X] Étape 6 : Bases de LangGraph
- [X] Étape 7 : Chatbot Agentic RAG
- [X] Étape 8 : LangGraph Studio
- [X] Étape 9 : Interface Streamlit

### C. MCP
- [X] Étape 10 : Serveur MCP (2 tools) + Inspector
- [X] Étape 11 : Agent LangChain client MCP (streamable-http)
- [X] Étape 12 : Agent n8n client MCP

### D. Synthèse
- [X] Étape 13 : SAV multi-agents (orchestrateur, agent documentaire via MCP, agent garantie)

## Installation
    uv sync
    ollama pull qwen3:4b
    ollama pull qwen3:1.7b
    ollama pull nomic-embed-text

    ## LangGraph Studio
![Exécution dans Studio](captures/execlanggraph.jpeg)

## Interface Streamlit
    uv run streamlit run app/streamlit_app.py

![Chatbot Streamlit](captures/streamlit.jpeg)

## Serveur MCP
    uv run python mcp_server/server.py      # http://localhost:24000/mcp

![Outils dans l'Inspector](captures/inspector_tools.jpg)
![Appel d'un outil](captures/inspector_run.jpg)

## Agent n8n (client MCP)
Workflow : `n8n/agent_rh_mcp.json` (à importer dans n8n via *Import from File*).
Chat Trigger → AI Agent, avec Ollama (qwen3:4b), Simple Memory et MCP Client Tool
connecté au serveur MCP en streamable-http (`http://127.0.0.1:24000/mcp`).

![Workflow n8n](captures/agentRHN8N.jpg)
