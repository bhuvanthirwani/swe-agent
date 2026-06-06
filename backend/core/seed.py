from backend.core.database import get_db_connection

def seed_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if seeded
    if cursor.execute("SELECT COUNT(*) FROM tools").fetchone()[0] > 0:
        print("Database already seeded.")
        return

    # Seed Tools
    tools = [
        ("read_file", "Reads file content from workspace", "read_file_func"),
        ("write_file", "Writes content to a file", "write_file_func"),
        ("run_tests", "Executes unit tests in the sandbox", "run_tests_func")
    ]
    cursor.executemany("INSERT INTO tools (name, description, code_reference) VALUES (?, ?, ?)", tools)
    
    # Seed LLMs
    cursor.execute("INSERT INTO llm_configs (provider, model_name, api_key, base_url) VALUES (?, ?, ?, ?)", 
                   ('openai', 'gpt-4o', 'sk-mock-key', 'https://api.openai.com/v1'))
                   
    # Seed Agents
    agents = [
        ("Router", "planner", "Routes the user request to the correct workflow", "You are an intelligent routing agent. Decide the best workflow path."),
        ("RequirementsAnalyst", "planner", "Analyzes requirements and sets context", "You are a product owner. Expand requirements into detailed technical specs."),
        ("Developer", "generator", "Writes code based on requirements", "You are an expert software developer. Write robust code using the provided tools."),
        ("CodeReviewer", "reviewer", "Reviews code for bugs and style", "You are a senior code reviewer. Ensure code quality and maintainability."),
        ("SecurityReviewer", "reviewer", "Checks code for security vulnerabilities", "You are a cybersecurity expert. Find and block security flaws.")
    ]
    cursor.executemany("INSERT INTO agents (name, type, description, system_prompt) VALUES (?, ?, ?, ?)", agents)
    
    # Link Agent LLMs (Give Developer primary LLM ID 1)
    cursor.execute("INSERT INTO agent_llms (agent_id, llm_id, is_primary) VALUES (3, 1, 1)")
    
    # Assign tools to Developer (Agent 3 gets tools 1 and 2)
    cursor.execute("INSERT INTO agent_tools (agent_id, tool_id) VALUES (3, 1)")
    cursor.execute("INSERT INTO agent_tools (agent_id, tool_id) VALUES (3, 2)")
    
    conn.commit()
    conn.close()
    print("Database seeded with default Agents, Tools, and LLM Configs.")

if __name__ == "__main__":
    seed_database()
