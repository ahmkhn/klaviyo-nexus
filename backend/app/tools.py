import httpx
import os
import contextvars
from mcp.types import Tool, TextContent

# 1. Context Var (Still needed, but we will manage it carefully in the router)
current_user_token = contextvars.ContextVar("current_user_token", default=None)

# 2. Tool Definitions (Hardened Schemas)
TOOLS = [
    # READ TOOL 1: Account Details
    Tool(
        name="get_account_details",
        description="Get details of the connected Klaviyo account (ID, Organization Name, Timezone).",
        inputSchema={
            "type": "object", 
            "properties": {},
            "additionalProperties": False # Strict Schema
        } 
    ),
    # READ TOOL 2: List Campaigns
    Tool(
        name="get_campaigns",
        description="Fetch the last 5 marketing campaigns with their IDs and Status.",
        inputSchema={
            "type": "object", 
            "properties": {},
            "additionalProperties": False
        }
    ),
    # WRITE TOOL: Create List
    Tool(
        name="create_list",
        description="Create a new subscriber list in Klaviyo. Returns the new List ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "list_name": {"type": "string", "description": "The name of the new list (e.g., 'VIP Customers')"}
            },
            "required": ["list_name"],
            "additionalProperties": False
        }
    )
]

# 3. Execution Logic (With Timeouts & Error Handling)
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    token = current_user_token.get()
    if not token:
        return [TextContent(type="text", text="Error: User is not authenticated via OAuth.")]

    headers = {
        "Authorization": f"Bearer {token}",
        "revision": "2024-10-15",
        "accept": "application/json",
        "content-type": "application/json"
    }

    # API Hardening: 10s timeout to prevent hanging
    async with httpx.AsyncClient(timeout=10.0) as client:
        
        # --- TOOL: Get Account Details ---
        if name == "get_account_details":
            resp = await client.get("https://a.klaviyo.com/api/accounts/", headers=headers)
            if resp.status_code == 401:
                return [TextContent(type="text", text="Error: OAuth Token Expired. Please re-login.")]
            if resp.status_code != 200:
                return [TextContent(type="text", text=f"API Error {resp.status_code}: {resp.text}")]
            
            data = resp.json().get("data", [])
            details = [f"Org: {acc['attributes']['contact_information']['organization_name']} (ID: {acc['id']})" for acc in data]
            return [TextContent(type="text", text="\n".join(details))]

        # --- TOOL: Get Campaigns ---
        elif name == "get_campaigns":
            resp = await client.get("https://a.klaviyo.com/api/campaigns/?page[size]=5", headers=headers)
            if resp.status_code != 200:
                return [TextContent(type="text", text=f"API Error {resp.status_code}: {resp.text}")]
            
            data = resp.json().get("data", [])
            if not data:
                return [TextContent(type="text", text="No campaigns found.")]
            
            summary = [f"ID: {d['id']} | Name: {d['attributes']['name']} | Status: {d['attributes']['status']}" for d in data]
            return [TextContent(type="text", text="\n".join(summary))]

        # --- TOOL: Create List ---
        elif name == "create_list":
            url = "https://a.klaviyo.com/api/lists/"
            payload = {
                "data": {
                    "type": "list",
                    "attributes": {
                        "name": arguments["list_name"]
                    }
                }
            }
            resp = await client.post(url, json=payload, headers=headers)
            
            if resp.status_code == 201:
                new_id = resp.json()["data"]["id"]
                return [TextContent(type="text", text=f"SUCCESS: Created list '{arguments['list_name']}' with ID: {new_id}")]
            else:
                return [TextContent(type="text", text=f"Failed to create list: {resp.text}")]

    raise ValueError(f"Tool {name} not found")