import httpx
import os
import contextvars
from mcp.types import Tool, TextContent
import uuid
import json

# 1. Context Var (Still needed, but we will manage it carefully in the router)
current_user_token = contextvars.ContextVar("current_user_token", default=None)

# actions waiting approval
PENDING_ACTIONS = {}



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
    # READ TOOL 3: Lists
    Tool(
        name="get_lists",
        description="Fetch existing subscriber lists with their IDs and profile counts.",
        inputSchema={
            "type": "object",
            "properties": {},
            "additionalProperties": False
        }
    ),
    # READ TOOL 4: Segments
    Tool(
        name="get_segments",
        description="Fetch available segments with their IDs and profile counts.",
        inputSchema={
            "type": "object",
            "properties": {},
            "additionalProperties": False
        }
    ),
    # 1. THE PROPOSER (Read-Only)
    # The AI calls this when it WANTS to do something.
    Tool(
        name="propose_action",
        description="Propose a modification (like creating a list) that requires user approval. You MUST provide the specific parameters (like 'list_name') for the chosen action.",
        inputSchema={
            "type": "object",
            "properties": {
                "action_type": {
                    "type": "string",
                    "enum": ["create_list"], 
                    "description": "The type of action to perform."
                },
                "list_name": {
                    "type": "string", 
                    "description": "REQUIRED if action_type is 'create_list'. The name of the new list."
                }
            },
            "required": ["action_type"],
            "additionalProperties": False
        }
    ),

    # 2. THE EXECUTOR (Write)
    # This is only called after the user clicks "Approve" in the UI.
    Tool(
        name="execute_action",
        description="Execute a previously proposed action using its Approval ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "approval_id": {"type": "string"},
                "list_name": {"type": "string", "description": "Fallback: If approval ID fails, provide list name here."}
            },
            "required": ["approval_id"],
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
            params = {
                "filter": "equals(messages.channel,'email')",
                "sort": "-created_at"
            }
            resp = await client.get("https://a.klaviyo.com/api/campaigns/", params=params, headers=headers)
            if resp.status_code != 200:
                return [TextContent(type="text", text=f"API Error {resp.status_code}: {resp.text}")]
            
            data = resp.json().get("data", [])
            if not data:
                return [TextContent(type="text", text="No email campaigns found.")]
            
            summary = [f"ID: {d['id']} | Name: {d['attributes']['name']} | Status: {d['attributes']['status']}" for d in data]
            req = resp.request
            print("METHOD:", req.method)
            print("URL:", req.url)
            print("BODY:", req.content)  # should be b"" for GET
            return [TextContent(type="text", text="\n".join(summary))]

        # --- TOOL: Get Lists ---
        elif name == "get_lists":
            resp = await client.get("https://a.klaviyo.com/api/lists/", headers=headers)
            if resp.status_code != 200:
                return [TextContent(type="text", text=f"API Error {resp.status_code}: {resp.text}")]
            
            data = resp.json().get("data", [])
            if not data:
                return [TextContent(type="text", text="No lists found.")]
            
            summary = []
            for item in data:
                attrs = item.get("attributes", {})
                summary.append(
                    f"ID: {item.get('id', 'unknown')} | Name: {attrs.get('name', 'Unknown')} | Profiles: {attrs.get('profile_count', 'n/a')}"
                )
            return [TextContent(type="text", text="\n".join(summary))]

        # --- TOOL: Get Segments ---
        elif name == "get_segments":
            resp = await client.get("https://a.klaviyo.com/api/segments/", headers=headers)
            if resp.status_code != 200:
                return [TextContent(type="text", text=f"API Error {resp.status_code}: {resp.text}")]
            
            data = resp.json().get("data", [])
            if not data:
                return [TextContent(type="text", text="No segments found.")]
            
            summary = []
            for item in data:
                attrs = item.get("attributes", {})
                summary.append(
                    f"ID: {item.get('id', 'unknown')} | Name: {attrs.get('name', 'Unknown')} | Profiles: {attrs.get('profile_count', 'n/a')}"
                )
            return [TextContent(type="text", text="\n".join(summary))]

        elif name == "propose_action":
            act_type = arguments.get("action_type")
            if not act_type:
                return [TextContent(type="text", text="Error: Missing 'action_type' in propose_action call.")]

            # Construct params from flattened arguments
            params = {}
            if act_type == "create_list":
                # Check top-level list_name
                l_name = arguments.get("list_name")
                if not l_name:
                    return [TextContent(type="text", text="Error: 'list_name' is required for create_list action.")]
                params["list_name"] = l_name
            
            # Generate a unique ID for this plan
            approval_id = str(uuid.uuid4())[:8]
            
            # Store it in memory
            PENDING_ACTIONS[approval_id] = {
                "type": act_type,
                "params": params,
                "description": f"Create {act_type.replace('_', ' ')}: {params.get('list_name', 'Unknown')}"
            }
            
            # Return a special JSON signal. 
            # The Agent will read this and tell the user: "I have a plan, please approve."
            return [TextContent(type="text", text=json.dumps({
                "status": "proposed",
                "approval_id": approval_id,
                "description": PENDING_ACTIONS[approval_id]["description"],
                "params": params
            }))]

        # Step 2: Execute (The actual API call)
        elif name == "execute_action":
            a_id = arguments.get("approval_id")
            action = PENDING_ACTIONS.get(a_id)
            
            # STATELESS FALLBACK:
            # If the server restarted, memory is wiped. 
            # If the user provides the list_name in the arguments, use it directly.
            list_name_fallback = arguments.get("list_name")
            
            if not action:
                if list_name_fallback:
                    action = {"type": "create_list", "params": {"list_name": list_name_fallback}}
                else:
                    return [TextContent(type="text", text="Error: Invalid or expired Approval ID (and no fallback data provided).")]
            
            # --- EXECUTE: Create List ---
            if action["type"] == "create_list":
                url = "https://a.klaviyo.com/api/lists/"
                payload = {
                    "data": {
                        "type": "list",
                        "attributes": {
                            "name": action["params"]["list_name"]
                        }
                    }
                }
                resp = await client.post(url, json=payload, headers=headers)
                
                # Cleanup: Remove the action so it can't be executed twice
                del PENDING_ACTIONS[a_id]
                
                if resp.status_code == 201:
                    new_id = resp.json()["data"]["id"]
                    return [TextContent(type="text", text=f"SUCCESS: Created list '{action['params']['list_name']}' (ID: {new_id})")]
                else:
                    return [TextContent(type="text", text=f"Failed to create list: {resp.text}")]

    raise ValueError(f"Tool {name} not found")
