import os
import shutil
import csv
import json
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP Server
app = FastMCP("OKF-Updater-MCP-Server")

# Excluded folders list
EXCLUDED_FOLDERS = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".idea",
    ".vscode",
    "dist",
    "build"
}

# Supported data and code extensions
SUPPORTED_EXTENSIONS = {
    # Data
    ".csv", ".tsv", ".json", ".sql", ".db", ".sqlite",
    # Code / Metadata
    ".py", ".js", ".ts", ".sh", ".yaml", ".yml", ".md"
}

def is_sensitive(path_str: str) -> bool:
    """
    Security Feature 1: Blocks access to sensitive files.
    Checks if a filename or any containing directory in the path starts with '.env'
    or contains 'secret', 'password', or 'api_key' (case-insensitive).
    """
    normalized_path = os.path.normpath(path_str).lower()
    filename = os.path.basename(normalized_path)
    
    # Check if filename is .env or starts with .env (e.g. .env.local)
    if filename.startswith(".env") or filename.endswith(".env"):
        return True
        
    sensitive_keywords = ["secret", "password", "api_key"]
    
    # Check if filename contains sensitive words
    if any(kw in filename for kw in sensitive_keywords):
        return True
        
    # Check each directory level for sensitive words or .env folders
    path_parts = normalized_path.split(os.sep)
    for part in path_parts:
        if part.startswith(".env") or any(kw in part for kw in sensitive_keywords):
            return True
            
    return False

def validate_project_path(project_path: str) -> str:
    """
    Helper to sanitize and return an absolute project path.
    """
    if not project_path:
        raise ValueError("Project path must be provided.")
    abs_path = os.path.abspath(project_path)
    if not os.path.exists(abs_path):
        raise ValueError(f"Project path does not exist: {abs_path}")
    return abs_path

def safe_resolve_file(project_path: str, file_path: str) -> str:
    """
    Helper to safely resolve a file path inside a project directory,
    protecting against path traversal and enforcing sensitive file blocks.
    """
    abs_project = validate_project_path(project_path)
    # Resolve absolute path of target file
    abs_file = os.path.abspath(os.path.join(abs_project, file_path))
    
    # Path Traversal Guard: Ensure file is inside the project directory
    if not abs_file.startswith(abs_project):
        raise PermissionError(f"Access Denied: Path traversal attempt blocked for {file_path}")
        
    # Security Feature 1 Check: Ensure it is not a sensitive file
    if is_sensitive(abs_file):
        raise PermissionError(f"Access Denied: File '{file_path}' contains sensitive credentials or configurations.")
        
    return abs_file

@app.tool()
def list_project_files(project_path: str) -> list[str]:
    """
    Lists data and code files in the project root recursively, skipping system/dependency directories
    and filtering out any sensitive files (e.g. .env, database passwords, api keys).
    
    Args:
        project_path: The absolute path to the project root.
    """
    abs_project = validate_project_path(project_path)
    eligible_files = []
    
    for root, dirs, files in os.walk(abs_project):
        # In-place modify dirs to skip excluded folders in walk recursion
        dirs[:] = [d for d in dirs if d not in EXCLUDED_FOLDERS and not is_sensitive(d)]
        
        for file in files:
            full_path = os.path.join(root, file)
            # Check if filename is sensitive
            if is_sensitive(full_path):
                continue
                
            # Filter by supported extensions to make scanning focused
            ext = os.path.splitext(file)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                rel_path = os.path.relpath(full_path, abs_project)
                eligible_files.append(rel_path)
                
    return eligible_files

@app.tool()
def get_csv_schema(file_path: str, project_path: str) -> dict:
    """
    Scans a CSV file to retrieve headers and a list of sample rows (first 5 rows)
    to help agents construct an AI-ready schema. Enforces strict security boundary checks.
    
    Args:
        file_path: The relative path to the CSV file within the project.
        project_path: The absolute path to the project root.
    """
    # Safe resolve applies path traversal protection and security keyword filtering
    abs_file_path = safe_resolve_file(project_path, file_path)
    
    if not os.path.exists(abs_file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    try:
        with open(abs_file_path, mode='r', encoding='utf-8-sig', errors='ignore') as f:
            reader = csv.reader(f)
            headers = next(reader, None)
            if not headers:
                return {"file": file_path, "status": "Empty CSV or no headers"}
                
            sample_rows = []
            for _ in range(5):
                row = next(reader, None)
                if row is None:
                    break
                sample_rows.append(row)
                
            return {
                "file_path": file_path,
                "headers": headers,
                "sample_rows": sample_rows,
                "num_columns": len(headers)
            }
    except Exception as e:
        return {"error": f"Failed to parse CSV schema: {str(e)}"}

@app.tool()
def write_okf_manifest(project_path: str, manifest_data: dict) -> str:
    """
    Writes the generated OKF JSON object to okf_manifest.json in the project root.
    Security Feature 2: If an okf_manifest.json already exists, it is automatically
    backed up as okf_manifest.json.bak.
    
    Args:
        project_path: The absolute path to the project root where manifest will be saved.
        manifest_data: The dictionary structure representing the OKF manifest.
    """
    abs_project = validate_project_path(project_path)
    manifest_filepath = os.path.join(abs_project, "okf_manifest.json")
    
    # Path traversal and sensitivity safety checks
    safe_resolve_file(project_path, "okf_manifest.json")
    
    backup_created = False
    # Security Feature 2: Backup existing manifest
    if os.path.exists(manifest_filepath):
        backup_filepath = os.path.join(abs_project, "okf_manifest.json.bak")
        shutil.copy2(manifest_filepath, backup_filepath)
        backup_created = True
        
    try:
        with open(manifest_filepath, mode='w', encoding='utf-8') as f:
            json.dump(manifest_data, f, indent=2, ensure_ascii=False)
            
        msg = f"Successfully wrote manifest to {manifest_filepath}."
        if backup_created:
            msg += f" (Existing manifest backed up to okf_manifest.json.bak)"
        return msg
    except Exception as e:
        raise IOError(f"Failed to write okf_manifest.json: {str(e)}")

if __name__ == "__main__":
    import sys
    print("Starting OKF Updater MCP Server via FastMCP...")
    app.run()
