# AI-Ready Metadata: The OKF Updater Agent

This project is an autonomous multi-agent system designed to scan existing codebases and data projects, analyze database structures and schemas (e.g. CSVs), and automatically generate an AI-readable metadata layer compliant with Google's **Open Knowledge Format (OKF)**.

This repository is submitted as a capstone project for the **5-Day AI Agents Course by Google**.

---

## 🏗️ Architecture & Interaction

The system relies on a clean separation of concerns, separating data collection and file system operations (Component A) from AI planning and format generation (Component B).

```
 ┌────────────────────────────────────────────────────────┐
 │                      User / Runner                     │
 └──────────────────────────┬─────────────────────────────┘
                            │ (1) Execute Pipeline
                            ▼
 ┌────────────────────────────────────────────────────────┐
 │           Agent Orchestration (agent_system.py)        │
 └──────────────────────────┬─────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼ (2) Scan files            ▼ (4) Convert to OKF JSON
 ┌──────────────────────────┐    ┌──────────────────────────┐
 │      Analyzer Agent      │    │     Formatter Agent      │
 └────────────┬─────────────┘    └────────────┬─────────────┘
              │                               │
              │ (3) Uses MCP Tools            │ (5) Invokes Write
              └─────────────┬─────────────────┘
                            ▼
 ┌────────────────────────────────────────────────────────┐
 │         Model Context Protocol (MCP) Server            │
 │                   (mcp_server.py)                      │
 ├────────────────────────────────────────────────────────┤
 │   🛡️ Security Boundary checks:                         │
 │   - Block sensitive files (.env, secrets, API keys)    │
 │   - Validate project directory bounds (no traversal)   │
 │   - Create backups of existing manifests               │
 └──────────────────────────┬─────────────────────────────┘
                            │
                            ▼
 ┌────────────────────────────────────────────────────────┐
 │              Target Project Workspace                  │
 └────────────────────────────────────────────────────────┘
```

1. **The MCP Server (`mcp_server.py`)** acts as the secure physical interface to the file system. It exposes tools for directory scanning, schema inspection, and manifest writing, while enforcing isolation boundaries.
2. **The ADK Multi-Agent System (`agent_system.py`)** serves as the cognitive layer.
   - **Analyzer Agent** explores the directory list and reads CSV dataset structures. It creates a detailed natural language summary.
   - **Formatter Agent** parses the summary, maps column schemas to the OKF format, and formats the output as a valid `okf_manifest.json` before writing it out.

---

## 🌟 Satisfying Capstone Criteria

This capstone project implements **three core concepts** covered in the course:

| Concept | Implementation Details in This Project |
| :--- | :--- |
| **1. Agent / Multi-Agent System (using ADK)** | Implemented via `google.adk.agents.Agent`. The system defines specialized agents (`AnalyzerAgent` and `FormatterAgent`) that communicate via a structured event runner, achieving a modular, collaborative pipeline instead of a monolithic setup. |
| **2. Model Context Protocol (MCP) Server** | Implemented using the `mcp` SDK and `FastMCP`. Exposes `@app.tool()` decorators for file system tasks, decoupling the agent's reasoning from the underlying platform implementation. |
| **3. Security & Safety Safeguards** | **Double-walled security**: (1) Enforces strict file system boundaries with path traversal checking, blocking attempts to escape the root directory; (2) Automatically blocks reads of sensitive files (e.g. `.env`, files containing `secret`, `password`, `api_key`); (3) Automatically backs up existing files as `.bak` prior to manifest writing to prevent data loss. |

---

## 📁 Repository Structure

- `mcp_server.py`: The Python MCP Server exposing tools and implementing the security module.
- `agent_system.py`: The Agent orchestrator setting up and running the ADK Multi-Agent pipeline.
- `okf_manifest.json`: A sample output file detailing the schema generated for the project data.
- `requirements.txt`: Project package dependencies list.
- `mock_data/`: Sample project workspace used to test pipeline execution.
  - `sales.csv`: A mock sales transaction dataset.
  - `.env`: A dummy environment config containing credential variables (used to test security blocks).

---

## 🚀 Setup & Execution

### 1. Prerequisites
- Python 3.10 or higher.
- A valid Gemini API Key.

### 2. Installation
Install the required packages in your development environment:
```bash
pip install -r requirements.txt
```

### 3. Run the Multi-Agent Pipeline
Set your API Key environment variable and launch the pipeline:

On **Windows PowerShell**:
```powershell
$env:GEMINI_API_KEY="your_actual_gemini_api_key"
python agent_system.py
```

On **Linux / macOS**:
```bash
export GEMINI_API_KEY="your_actual_gemini_api_key"
python agent_system.py
```

The script will:
1. Scan the `mock_data/` directory using the secure MCP tools.
2. Read the headers and row samples of `sales.csv`.
3. Auto-detect that `.env` is sensitive and block its analysis.
4. Auto-generate and save the `okf_manifest.json` file in the root.

---

## 🔒 Security Policy Highlights

1. **Path Traversal Shield**: The resolver canonicalizes absolute paths via `os.path.abspath` and throws an error if any file lies outside the target project folder root.
2. **Sensitive Data Blocker**: Filenames and path levels are inspected for blacklisted words:
   - `secret` (e.g., `client_secret.json`)
   - `password` (e.g., `db_passwords.txt`)
   - `api_key` (e.g., `keys.yaml`)
   - `.env` files (e.g., `.env.production`)
3. **Data Loss Guard**: When writing `okf_manifest.json`, the server detects existing manifests and creates a `.bak` backup copy first.
