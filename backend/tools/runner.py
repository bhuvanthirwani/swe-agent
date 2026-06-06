import subprocess
import tempfile
import os
import shutil

EXECUTION_TIMEOUT = 15

def execute_code(code: str, language: str = 'python') -> str:
    \"\"\"
    Execute code in a sandboxed temp directory.
    \"\"\"
    temp_dir = tempfile.mkdtemp(prefix="mao-exec-")
    try:
        if language == 'python':
            filename = 'script.py'
            cmd = ['python', filename]
        elif language == 'javascript':
            filename = 'script.js'
            cmd = ['node', filename]
        elif language == 'bash':
            filename = 'script.sh'
            cmd = ['bash', filename]
        else:
            return f"Error: Unsupported language {language}"
            
        file_path = os.path.join(temp_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(code)
            
        result = subprocess.run(
            cmd,
            cwd=temp_dir,
            capture_output=True,
            text=True,
            timeout=EXECUTION_TIMEOUT
        )
        
        output = result.stdout
        if result.stderr:
            output += f"\\n--- STDERR ---\\n{result.stderr}"
            
        if len(output) > 8000:
            return output[:8000] + "\\n... [output truncated]"
            
        return output if output else "Execution successful (no output)."
        
    except subprocess.TimeoutExpired:
        return f"Error: Execution timed out after {EXECUTION_TIMEOUT} seconds."
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
