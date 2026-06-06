import os

WORKSPACE_ROOT = os.path.join(os.getcwd(), 'workspace')

def _resolve_safe_path(file_path: str) -> str:
    resolved = os.path.abspath(os.path.join(WORKSPACE_ROOT, file_path))
    if not resolved.startswith(os.path.abspath(WORKSPACE_ROOT)):
        raise ValueError("Path traversal attempt blocked")
    return resolved

def read_file(file_path: str) -> str:
    """
    Safely reads a file from the workspace directory.
    """
    try:
        resolved = _resolve_safe_path(file_path)
        if not os.path.exists(resolved):
            return f"Error: File {file_path} does not exist."
            
        with open(resolved, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if len(content) > 4000:
            return content[:4000] + '\\n... [truncated for brevity]'
        return content
    except Exception as e:
        return f"Error reading file: {str(e)}"

def list_files(dir_path: str = '.') -> str:
    """
    Lists files in a workspace directory.
    """
    try:
        resolved = _resolve_safe_path(dir_path)
        if not os.path.exists(resolved) or not os.path.isdir(resolved):
            return f"Error: Directory {dir_path} does not exist."
            
        entries = []
        for entry in os.listdir(resolved):
            if os.path.isdir(os.path.join(resolved, entry)):
                entries.append(f"{entry}/")
            else:
                entries.append(entry)
        return "\\n".join(entries) if entries else "Directory is empty."
    except Exception as e:
        return f"Error listing files: {str(e)}"

def edit_code(file_path: str, target_content: str, replacement_content: str) -> str:
    """
    Make surgical edits to a file by replacing target_content with replacement_content.
    """
    try:
        resolved = _resolve_safe_path(file_path)
        if not os.path.exists(resolved):
            return f"Error: File {file_path} does not exist."
            
        with open(resolved, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if target_content not in content:
            return "Error: Target content not found in file. Ensure exact match including whitespace."
            
        new_content = content.replace(target_content, replacement_content, 1)
        
        with open(resolved, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        return f"Successfully updated {file_path}."
    except Exception as e:
        return f"Error editing code: {str(e)}"
