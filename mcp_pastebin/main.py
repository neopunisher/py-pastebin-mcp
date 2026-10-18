import os

import httpx
from fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("Pastebin")

PASTEBIN_API_URL = "https://pastebin.com/api/api_post.php"

@mcp.tool()
async def login(
    user_name: str,
    password: str,
    api_dev_key: str | None = None
) -> str:
    """
    Login to Pastebin to get a User API Key for private pastes and listing.
    
    Args:
        user_name: Your Pastebin username.
        password: Your Pastebin password.
        api_dev_key: Your Pastebin Developer API Key.
    """
    key = api_dev_key or os.environ.get("PASTEBIN_DEV_KEY")
    if not key:
        return "Error: api_dev_key missing."

    data = {
        "api_dev_key": key,
        "api_user_name": user_name,
        "api_user_password": password,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post("https://pastebin.com/api/api_login.php", data=data)
        
    return response.text

@mcp.tool()
async def create_paste(
    code: str,
    name: str | None = None,
    format: str | None = None,
    expire_date: str | None = "1H",
    private: int = 1,
    api_dev_key: str | None = None,
    api_user_key: str | None = None
) -> str:
    """
    Create a new paste on Pastebin.
    
    Args:
        code: The content of the paste.
        name: Name or title of the paste.
        format: Syntax highlighting format (e.g., 'python', 'javascript').
        expire_date: Expiration time (N=Never, 10M, 1H, 1D, 1W, 2W, 1M, 6M, 1Y). Default is 1H.
        private: Privacy level (0=Public, 1=Unlisted, 2=Private). Private requires api_user_key.
        api_dev_key: Your Pastebin Developer API Key.
        api_user_key: Your Pastebin User Key (from login). Required for private pastes.
    """
    key = api_dev_key or os.environ.get("PASTEBIN_DEV_KEY")
    user_key = api_user_key or os.environ.get("PASTEBIN_USER_KEY")
    
    if not key:
        return "Error: api_dev_key missing."

    data = {
        "api_dev_key": key,
        "api_user_key": user_key,
        "api_option": "paste",
        "api_paste_code": code,
        "api_paste_private": private,
        "api_paste_name": name,
        "api_paste_expire_date": expire_date,
        "api_paste_format": format,
    }
    
    data = {k: v for k, v in data.items() if v is not None}

    async with httpx.AsyncClient() as client:
        response = await client.post(PASTEBIN_API_URL, data=data)
        
    return response.text

@mcp.tool()
async def list_user_pastes(
    api_dev_key: str | None = None,
    api_user_key: str | None = None,
    limit: int = 50
) -> str:
    """
    List your pastes (requires login).
    
    Args:
        api_dev_key: Your Pastebin Developer API Key.
        api_user_key: Your Pastebin User Key.
        limit: Number of results (1-1000, default 50).
    """
    key = api_dev_key or os.environ.get("PASTEBIN_DEV_KEY")
    user_key = api_user_key or os.environ.get("PASTEBIN_USER_KEY")
    
    if not key or not user_key:
        return "Error: api_dev_key or api_user_key missing. Login first."

    data = {
        "api_dev_key": key,
        "api_user_key": user_key,
        "api_option": "list",
        "api_results_limit": limit,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(PASTEBIN_API_URL, data=data)
        
    return response.text

@mcp.tool()
async def delete_paste(
    paste_key: str,
    api_dev_key: str | None = None,
    api_user_key: str | None = None
) -> str:
    """
    Delete a paste (requires login/api_user_key).
    
    Args:
        paste_key: The unique key of the paste to delete (e.g., 'vP9H81M1').
        api_dev_key: Your Pastebin Developer API Key.
        api_user_key: Your Pastebin User Key.
    """
    key = api_dev_key or os.environ.get("PASTEBIN_DEV_KEY")
    user_key = api_user_key or os.environ.get("PASTEBIN_USER_KEY")
    
    if not key or not user_key:
        return "Error: api_dev_key and api_user_key are required to delete pastes."

    data = {
        "api_dev_key": key,
        "api_user_key": user_key,
        "api_option": "delete",
        "api_paste_key": paste_key,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(PASTEBIN_API_URL, data=data)
        
    return response.text

@mcp.tool()
async def stop() -> str:
    """
    Stop the MCP server. This will terminate the process.
    """
    import sys
    import threading
    
    # Schedule exit after returning the response
    threading.Timer(0.1, lambda: sys.exit(0)).start()
    return "Server is shutting down..."

@mcp.tool()
async def get_trending_pastes(api_dev_key: str | None = None) -> str:
    """
    Get the top trending pastes on Pastebin.
    
    Args:
        api_dev_key: Your Pastebin Developer API Key.
    """
    key = api_dev_key or os.environ.get("PASTEBIN_DEV_KEY")
    if not key:
        return "Error: Pastebin Developer API Key is missing."

    params = {
        "api_dev_key": key,
        "api_option": "trends",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(PASTEBIN_API_URL, data=params)
        
    if response.status_code == 200:
        return response.text
    else:
        return f"HTTP Error {response.status_code}: {response.text}"

def main():
    mcp.run()

if __name__ == "__main__":
    main()
