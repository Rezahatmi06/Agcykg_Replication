
# AgCyRAG: an Agentic Knowledge Graph based RAG Framework for Automated Security Analysis

AgCyRAG is a hybrid Agentic Retrieval-Augmented Generation (RAG) framework designed to improve cybersecurity analysis by integrating Knowledge Graph (KG) reasoning with vector-based retrieval.
It enables factual grounding of Large Language Model (LLM)-powered analyses while handling heterogeneous structured and unstructured data (e.g., security log sources)
## Core Components

- Multi-Agent System (LangGraph): The primary application logic that orchestrates the entire workflow. It includes specialized agents for validating questions, querying databases, reflecting on results, and synthesizing final answers
- Neo4j Knowledge Graph: A graph database storing structured cybersecurity data (e.g., from the MITRE ATT&CK framework), which is queried using the Cypher language.
- MCP RDF Explorer: Model Context Protocol (MCP) server that provides a conversational interface for RDF-based Knowledge Graph (Turtle) exploration and analysis in local file mode or SPARQL endpoint mode. (https://github.com/emekaokoye/mcp-rdf-explorer)

## Setup and Installation

How to use

Make sure that you already have uv installed on your desktop, if not then here's the installation guide : https://docs.astral.sh/uv/getting-started/installation/ 

```bash
  git clone <this-project>
  cd <this-project>
  uv sync
```
- make sure that you have cloned the MCP RDF Explorer repository, outside this multi-agents-cykg-rag repository/folder
- add your .ttl (rdf schema) to $ ls mcp-rdf-explorer/src/mcp-rdf-explorer/
- one level with the server.py code
- setup the browser_mcp.json located in root of multi-agents-cykg-rag repository
- which look like this (you can see more specific explanation of this step in MCP-RDF-Explorer repo [MCP RDF Explorer](https://github.com/emekaokoye/mcp-rdf-explorer)) :
```json
  {
  "mcpServers": {
    "rdf_explorer": {
      "command": "D:\\Project\\github\\mcp-rdf-explorer\\venv\\Scripts\\python.exe",
      "args": ["D:\\Project\\github\\mcp-rdf-explorer\\src\\mcp-rdf-explorer\\server.py", "--triple-file", "statements.ttl"]
    }
  }
}
```

Make sure again that the .env file is filled !!!
```bash
OPENAI_API_KEY=
LANGCHAIN_API_KEY=
LANGCHAIN_TRACING_V2=
LANGCHAIN_ENDPOINT=
LANGCHAIN_PROJECT=
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=    
NEO4J_PASSWORD_ICS=
NEO4J_DATABASE=

NEO4J_AURA=
NEO4J_AURA_USERNAME=
NEO4J_AURA_PASSWORD=
NEO4J_AURA_DATABASE=
```

Setup is completed, now you can run the program!!!
```bash
  uv run -m src.run -- "Your question here"
```


## Features

- **Multi-agent workflow**: Uses LangGraph to manage the workflow between agents (guardrails, vector search, cypher search, MCP RDF, reflection, and synthesizer).

- **Guardrails**: Ensures the questions asked are relevant to the cybersecurity domain.

- **Vector & Cypher Search**: Searches for answers from a vector and graph database (Neo4j) with automatic iteration and reflection if results are insufficient.

- **MCP RDF Agent**: Integrates RDF-based search to enrich the context of answers.

- **Synthesizer**: Combines results from multiple sources into a comprehensive final answer.

- **Logging & Configuration**: Supports structured logging and configuration via .env files.


## Project Structure

```bash

no-log-multi-agents-cykg-rag/
├── src/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── mcp_rdf_agent.py
│   │   ├── cypher_agent.py
│   │   ├── reflection_agents.py
│   │   └── vector_agent.py
│   ├── chains/
│   │   ├── __init__.py
│   │   ├── guardrails.py
│   │   ├── review.py
│   │   └── synthesizer.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── state.py
│   │   └── workflow.py
│   ├── log/
│   │   └── (a log file will be created here)
│   ├── utils/
│   │   ├── __init__.py
│   │   └── logging_config.py
│   └── run.py
└── .env


```

