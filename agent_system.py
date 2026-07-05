import os
import asyncio
import json
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Import the tool functions from Component A (MCP Server)
from mcp_server import list_project_files, get_csv_schema, write_okf_manifest

# Setup model name (using recommended Gemini flash model)
MODEL_NAME = "gemini-2.5-flash"

# Define Component B: ADK Agents

# 1. Agent 1: Analyzer Agent
# Responsible for listing files and scanning CSV schemas.
analyzer_agent = Agent(
    name="AnalyzerAgent",
    model=MODEL_NAME,
    instruction=(
        "You are the Analyzer Agent, a metadata parsing expert.\n"
        "Your task is to scan the project directory, identify the data and code files, "
        "and read the schemas of the CSV files using the provided tools.\n\n"
        "Instructions:\n"
        "1. List files in the project path using `list_project_files`.\n"
        "2. For each CSV file discovered, fetch its headers and sample rows using `get_csv_schema`.\n"
        "3. Synthesize this information into a clear, detailed summary containing:\n"
        "   - Estimated project domain and overall purpose.\n"
        "   - The folder layout and list of files.\n"
        "   - Schemas of data files (columns, data types, sample values).\n"
        "   - Potential AI agent use cases for these datasets.\n\n"
        "Do NOT attempt to read sensitive files (like .env or passwords). "
        "Maintain focus on code and data structures."
    ),
    tools=[list_project_files, get_csv_schema]
)

# 2. Agent 2: Formatter Agent
# Responsible for taking the Analyzer Agent's summary and formatting it into a strict OKF JSON manifest,
# then writing it to the root of the project.
formatter_agent = Agent(
    name="FormatterAgent",
    model=MODEL_NAME,
    instruction=(
        "You are the Formatter Agent, an expert in Open Knowledge Format (OKF) specifications.\n"
        "Your task is to take the project summary from the Analyzer Agent and construct "
        "a strict, valid JSON manifest according to the OKF specification.\n\n"
        "Your output must conform to this schema:\n"
        "{\n"
        "  \"okf_version\": \"1.0\",\n"
        "  \"project_metadata\": {\n"
        "    \"name\": \"Name of project\",\n"
        "    \"description\": \"Purpose summary\",\n"
        "    \"categories\": [\"e.g., finance, retail, analytics\"],\n"
        "    \"tags\": [\"e.g., data-sharing, sales\"],\n"
        "    \"last_updated\": \"2026-07-05T21:01:07Z\"\n"
        "  },\n"
        "  \"resources\": [\n"
        "    {\n"
        "      \"path\": \"relative/path/to/data.csv\",\n"
        "      \"type\": \"dataset\",\n"
        "      \"format\": \"csv\",\n"
        "      \"description\": \"Description of the dataset\",\n"
        "      \"schema\": {\n"
        "        \"fields\": [\n"
        "          {\"name\": \"col_name\", \"type\": \"data_type\", \"description\": \"Description\"}\n"
        "        ],\n"
        "        \"primary_key\": \"key_column\"\n"
        "      },\n"
        "      \"stats\": {\n"
        "        \"sample_rows_analyzed\": 5,\n"
        "        \"total_columns\": 6\n"
        "      }\n"
        "    }\n"
        "  ],\n"
        "  \"agent_instructions\": \"Guidelines for other AI agents to query/analyze this data.\"\n"
        "}\n\n"
        "Once you have generated the JSON structure, invoke the `write_okf_manifest` tool "
        "to save the manifest to the project's root.\n\n"
        "Provide a summary of the tool invocation result as your final output."
    ),
    tools=[write_okf_manifest]
)

# Pipeline Orchestration

def _extract_text(event) -> str:
    """
    Safely extract text from an ADK 2.x Event.
    Text lives in event.content.parts[*].text for model response events.
    """
    if event.content and event.content.parts:
        return "".join(
            part.text for part in event.content.parts if hasattr(part, "text") and part.text
        )
    return ""


async def run_multi_agent_pipeline(project_path: str):
    """
    Orchestrates the collaboration between Analyzer Agent and Formatter Agent.
    Each agent phase uses its own isolated session to prevent history contamination.
    """
    print(f"=== Initializing OKF Updater Pipeline ===")
    print(f"Target Project Path: {project_path}\n")

    user_id = "developer"

    # ── PHASE 1: Analyzer Agent ────────────────────────────────────────────────
    print("--- [Phase 1: Analyzing Project Structure & Schemas] ---")

    session_service_p1 = InMemorySessionService()
    analyzer_runner = Runner(
        agent=analyzer_agent,
        app_name="OKF-Updater-P1",
        session_service=session_service_p1,
    )
    session_p1 = await session_service_p1.create_session(
        app_name="OKF-Updater-P1",
        user_id=user_id,
        session_id="okf_session_analyzer",
    )

    analyzer_prompt = f"Please analyze the project at path: {project_path}"
    content_p1 = types.Content(role="user", parts=[types.Part.from_text(text=analyzer_prompt)])

    # Collect ALL streamed text (intermediate + final) for the handoff payload.
    summary_text = ""
    async for event in analyzer_runner.run_async(
        user_id=user_id,
        session_id=session_p1.id,
        new_message=content_p1,
    ):
        text = _extract_text(event)
        if text:
            print(text, end="", flush=True)
            summary_text += text          # accumulate every chunk, not just final

    print("\n\n--- [Phase 1 Complete] ---\n")
    print(f"[DEBUG] Summary text captured: {len(summary_text)} chars\n")

    # ── PHASE 2: Formatter Agent ───────────────────────────────────────────────
    print("--- [Phase 2: Generating and Writing OKF Manifest] ---")

    session_service_p2 = InMemorySessionService()
    formatter_runner = Runner(
        agent=formatter_agent,
        app_name="OKF-Updater-P2",
        session_service=session_service_p2,
    )
    session_p2 = await session_service_p2.create_session(
        app_name="OKF-Updater-P2",
        user_id=user_id,
        session_id="okf_session_formatter",
    )

    formatter_prompt = (
        f"Below is the project summary from the Analyzer Agent.\n"
        f"Please format it as a valid OKF JSON manifest and write it to the "
        f"project root at: {project_path}\n\n"
        f"Project Summary:\n{summary_text}"
    )
    content_p2 = types.Content(role="user", parts=[types.Part.from_text(text=formatter_prompt)])

    formatter_response = ""
    async for event in formatter_runner.run_async(
        user_id=user_id,
        session_id=session_p2.id,
        new_message=content_p2,
    ):
        # ── Diagnostic: print every event type so tool calls are visible ──────
        author = getattr(event, "author", "?")
        is_final = event.is_final_response()
        fn_calls = event.get_function_calls()
        fn_resps  = event.get_function_responses()

        if fn_calls:
            for fc in fn_calls:
                print(f"\n[TOOL CALL]  {fc.name}({json.dumps(fc.args, ensure_ascii=False)})", flush=True)
        if fn_resps:
            for fr in fn_resps:
                print(f"\n[TOOL RESP]  {fr.name} → {str(fr.response)[:300]}", flush=True)

        text = _extract_text(event)
        if text:
            print(text, end="", flush=True)
            formatter_response += text

    print("\n\n--- [Phase 2 Complete] ---\n")
    print("=== Pipeline Execution Finished successfully ===")

if __name__ == "__main__":
    # Check for Gemini API key
    if not os.environ.get("GEMINI_API_KEY"):
        print("WARNING: GEMINI_API_KEY environment variable is not set.")
        print("Please set it in your environment (e.g., $env:GEMINI_API_KEY='your_key') to run the agents.\n")
        
    # Default target is our mock_data directory
    default_project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "mock_data"))
    
    # Run pipeline
    try:
        asyncio.run(run_multi_agent_pipeline(default_project_dir))
    except Exception as e:
        print(f"\nError running pipeline: {e}")
