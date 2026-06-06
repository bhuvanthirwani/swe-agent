import os
import httpx
from pydantic import BaseModel
from typing import List, Dict, Optional

class GitHubMCPClient:
    def __init__(self, mcp_url: str = None):
        self.mcp_url = mcp_url or os.getenv("GITHUB_MCP_URL")
        if not self.mcp_url:
            raise ValueError("GITHUB_MCP_URL is not set.")
            
    async def list_repositories(self) -> List[str]:
        # Example implementation for listing repositories from MCP
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.mcp_url}/repos")
            response.raise_for_status()
            return response.json().get("repositories", [])
            
    async def get_tree(self, repo: str, branch: str = "main") -> Dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.mcp_url}/repos/{repo}/branches/{branch}/tree")
            response.raise_for_status()
            return response.json()
            
    async def get_readme(self, repo: str) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.mcp_url}/repos/{repo}/readme")
            response.raise_for_status()
            return response.json().get("content", "")
