import httpx
import os
import contextvars
from mcp.types import Tool, TextContent
import uuid
import json
import random
import hashlib

def get_klaviyo_headers(token: str, *, include_content_type: bool = False):
    headers = {
        "Authorization": f"Bearer {token}",
        "revision": "2024-10-15",
        "accept": "application/vnd.api+json",
    }
    if include_content_type:
        headers["content-type"] = "application/vnd.api+json"
    return headers

# 1. Context Var (Still needed, but we will manage it carefully in the router)
current_user_token = contextvars.ContextVar("current_user_token", default=None)

# actions waiting approval
PENDING_ACTIONS = {}

# Store last created resources per user/session (in-memory)
LAST_CONTEXT = {}

def _user_key(token: str) -> str:
    # avoid storing raw token as a dict key
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:12]

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
        description=(
            "Propose an action that requires user approval. Always include a "
            "'parameters' object with the relevant fields."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "action_type": {
                    "type": "string",
                    "enum": [
                        "create_list",
                        "create_vip_audience",
                        "create_campaign_draft",
                    ],
                },
                "parameters": {
                    "type": "object",
                    "properties": {
                        # create_list
                        "list_name": {"type": "string"},
                        # create_vip_audience
                        "min_spend": {"type": "integer"},
                        "seed_count": {"type": "integer"},
                        # create_campaign_draft
                        "list_id": {"type": "string"},
                        "campaign_name": {"type": "string"},
                        "subject": {"type": "string"},
                        "preview_text": {"type": "string"},
                        "from_email": {"type": "string"},
                        "from_label": {"type": "string"},
                        "reply_to_email": {"type": "string"},
                        "label": {"type": "string"},
                    },
                    "additionalProperties": False,
                },
            },
            "required": ["action_type", "parameters"],
            "additionalProperties": False,
        },
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
                "list_name": {
                    "type": "string",
                    "description": "Fallback: If approval ID fails, provide list name here."
                },
                "list_id": {
                    "type": "string",
                    "description": "Fallback: List ID for create_campaign_draft if approval ID fails."
                },
                "campaign_name": {
                    "type": "string",
                    "description": "Fallback: Campaign name for create_campaign_draft if approval ID fails."
                },
                "subject": {
                    "type": "string",
                    "description": "Optional: Email subject line to apply to the campaign message."
                },
                "preview_text": {
                    "type": "string",
                    "description": "Optional: Email preview text to apply to the campaign message."
                }
            },
            "required": ["approval_id"],
            "additionalProperties": False
        }
    )
]

# 3. Execution Logic (With Timeouts & Error Handling)
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    print("TOOL ARGS:", name, arguments, flush=True)
    token = current_user_token.get()
    if not token:
        return [TextContent(type="text", text="Error: User is not authenticated via OAuth.")]

    headers_get = get_klaviyo_headers(token, include_content_type=False)
    headers_post = get_klaviyo_headers(token, include_content_type=True)

    # API Hardening: 10s timeout to prevent hanging
    async with httpx.AsyncClient(timeout=10.0) as client:
        
        # --- TOOL: Get Account Details ---
        if name == "get_account_details":
            resp = await client.get("https://a.klaviyo.com/api/accounts/", headers=headers_get)
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
            resp = await client.get("https://a.klaviyo.com/api/campaigns/", params=params, headers=headers_get)
            if resp.status_code != 200:
                return [TextContent(type="text", text=f"API Error {resp.status_code}: {resp.text}")]
            
            data = resp.json().get("data", [])
            if not data:
                return [TextContent(type="text", text="No email campaigns found.")]
            
            summary = [f"ID: {d['id']} | Name: {d['attributes']['name']} | Status: {d['attributes']['status']}" for d in data]
            return [TextContent(type="text", text="\n".join(summary))]

        # --- TOOL: Get Lists ---
        elif name == "get_lists":
            resp = await client.get("https://a.klaviyo.com/api/lists/", headers=headers_get)
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
            resp = await client.get("https://a.klaviyo.com/api/segments/", headers=headers_get)
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
            parameters = arguments.get("parameters") or {}

            if not act_type:
                return [
                    TextContent(type="text", text="Error: Missing 'action_type' in propose_action.")
                ]

            params = {}
            description = ""

            if act_type == "create_list":
                l_name = parameters.get("list_name")
                if not l_name:
                    return [
                        TextContent(
                            type="text",
                            text="Error: parameters.list_name is required for create_list.",
                        )
                    ]
                params["list_name"] = l_name
                description = f"Create list: {l_name}"

            elif act_type == "create_vip_audience":
                params["min_spend"] = int(parameters.get("min_spend", 300))
                params["seed_count"] = int(parameters.get("seed_count", 3))
                description = (
                    f"Create VIP audience (demo list) for spend >= ${params['min_spend']} "
                    f"(seed {params['seed_count']} VIP profiles)"
                )

            elif act_type == "create_campaign_draft":
                uk = _user_key(token)
                last_list_id = (LAST_CONTEXT.get(uk) or {}).get("last_list_id")

                list_id = parameters.get("list_id") or last_list_id
                if not list_id:
                    return [
                        TextContent(
                            type="text",
                            text=(
                                "Error: parameters.list_id is required for create_campaign_draft "
                                "(or create a VIP/list first so I can reuse the last list)."
                            ),
                        )
                    ]

                campaign_name = parameters.get("campaign_name", "Nexus Draft Campaign")
                subject = parameters.get("subject", "A special offer for you")
                preview_text = parameters.get(
                    "preview_text", "Limited time—don’t miss out."
                )
                message_label = parameters.get("label", "Nexus Draft Message")

                # Hardcoded for now (fine for demo). Just ensure these are valid in Klaviyo.
                from_email = parameters.get("from_email") or "ahmedkhan@umass.edu"
                from_label = parameters.get("from_label") or "Nexus AI"
                reply_to_email = parameters.get("reply_to_email") or "ahmedkhan@umass.edu"

                params.update(
                    {
                        "list_id": list_id,
                        "campaign_name": campaign_name,
                        "subject": subject,
                        "preview_text": preview_text,
                        "label": message_label,
                        "from_email": from_email,
                        "from_label": from_label,
                        "reply_to_email": reply_to_email,
                    }
                )

                description = (
                    f"Create email campaign draft '{campaign_name}' targeting list {list_id} "
                    f"(subject='{subject}')"
                )

            else:
                return [
                    TextContent(
                        type="text", text=f"Error: Unsupported action_type '{act_type}'."
                    )
                ]

            # IMPORTANT: you were missing everything below
            approval_id = str(uuid.uuid4())[:8]
            PENDING_ACTIONS[approval_id] = {
                "type": act_type,
                "params": params,
                "description": description,
            }

            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "status": "proposed",
                            "approval_id": approval_id,
                            "description": description,
                            "params": params,
                        }
                    ),
                )
            ]

        # Step 2: Execute (The actual API call)
        elif name == "execute_action":
            a_id = arguments.get("approval_id")
            action = PENDING_ACTIONS.get(a_id)

            # STATELESS FALLBACK:
            list_name_fallback = arguments.get("list_name")
            list_id_fallback = arguments.get("list_id")
            campaign_name_fallback = arguments.get("campaign_name")
            subject_fallback = arguments.get("subject")
            preview_text_fallback = arguments.get("preview_text")
            from_email_fallback = arguments.get("from_email") or os.getenv("DEFAULT_FROM_EMAIL")
            from_label_fallback = arguments.get("from_label") or os.getenv("DEFAULT_FROM_LABEL")
            reply_to_email_fallback = arguments.get("reply_to_email") or os.getenv(
                "DEFAULT_REPLY_TO_EMAIL"
            )
            label_fallback = arguments.get("label") or "Nexus Draft Message"

            if not action:
                if list_name_fallback:
                    action = {"type": "create_list", "params": {"list_name": list_name_fallback}}
                elif list_id_fallback and campaign_name_fallback:
                    action = {
                        "type": "create_campaign_draft",
                        "params": {
                            "list_id": list_id_fallback,
                            "campaign_name": campaign_name_fallback,
                            "subject": subject_fallback or "A special offer for you",
                            "preview_text": preview_text_fallback or "Limited time—don’t miss out.",
                            "from_email": from_email_fallback,
                            "from_label": from_label_fallback,
                            "reply_to_email": reply_to_email_fallback,
                            "label": label_fallback,
                        },
                    }
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
                resp = await client.post(url, json=payload, headers=headers_post)
                
                # Cleanup: Remove the action so it can't be executed twice
                if a_id in PENDING_ACTIONS:
                    del PENDING_ACTIONS[a_id]
                
                if resp.status_code == 201:
                    new_id = resp.json()["data"]["id"]

                    # store last list id for convenience
                    uk = _user_key(token)
                    LAST_CONTEXT[uk] = {**(LAST_CONTEXT.get(uk) or {}), "last_list_id": new_id}

                    return [TextContent(type="text", text=f"SUCCESS: Created list '{action['params']['list_name']}' (ID: {new_id})")]
                else:
                    return [TextContent(type="text", text=f"Failed to create list: {resp.text}")]

            # --- EXECUTE: Create VIP Audience (demo list + seed VIP profiles + add to list) ---
            if action["type"] == "create_vip_audience":
                min_spend = action["params"].get("min_spend", 300)
                seed_count = action["params"].get("seed_count", 3)

                list_name = f"VIP Audience (demo): ${min_spend}+"
                url_list = "https://a.klaviyo.com/api/lists/"
                payload_list = {"data": {"type": "list", "attributes": {"name": list_name}}}

                resp_list = await client.post(
                    url_list, json=payload_list, headers=headers_post
                )
                if resp_list.status_code != 201:
                    return [
                        TextContent(
                            type="text",
                            text=f"Failed to create VIP list container: {resp_list.text}",
                        )
                    ]

                list_id = resp_list.json()["data"]["id"]

                # store last list id so campaign creation can reuse it
                uk = _user_key(token)
                LAST_CONTEXT[uk] = {**(LAST_CONTEXT.get(uk) or {}), "last_list_id": list_id}

                suffix = str(random.randint(1000, 9999))

                created_emails = []
                for i in range(seed_count):
                    email = f"vip.user{i+1}.{suffix}@example.com"
                    spend = min_spend + (50 * (i + 1))

                    payload_p = {
                        "data": {
                            "type": "profile",
                            "attributes": {
                                "email": email,
                                "properties": {
                                    "nexus_demo_spend_90d": spend,
                                    "nexus_demo_is_vip": True,
                                },
                            },
                        }
                    }
                    resp_p = await client.post(
                        "https://a.klaviyo.com/api/profiles/",
                        json=payload_p,
                        headers=headers_post,
                    )
                    if resp_p.status_code == 201:
                        pid = resp_p.json()["data"]["id"]
                        url_rel = (
                            f"https://a.klaviyo.com/api/lists/{list_id}/relationships/profiles/"
                        )
                        payload_rel = {"data": [{"type": "profile", "id": pid}]}
                        resp_rel = await client.post(
                            url_rel, json=payload_rel, headers=headers_post
                        )
                        if resp_rel.status_code in (200, 201, 204):
                            created_emails.append(f"{email} (${spend})")

                if a_id in PENDING_ACTIONS:
                    del PENDING_ACTIONS[a_id]

                return [
                    TextContent(
                        type="text",
                        text=(
                            f"SUCCESS: Created VIP List '{list_name}' (ID: {list_id}).\n"
                            f"Seeded+added {len(created_emails)} VIP profiles:\n"
                            + "\n".join(created_emails)
                        ),
                    )
                ]

            # --- EXECUTE: Create Campaign Draft targeting an existing list ---
            if action["type"] == "create_campaign_draft":
                list_id = action["params"]["list_id"]
                campaign_name = action["params"]["campaign_name"]
                subject = action["params"]["subject"]
                preview_text = action["params"].get("preview_text", "")
                from_email = action["params"].get("from_email")
                from_label = action["params"].get("from_label")
                reply_to_email = action["params"].get("reply_to_email")
                msg_label = action["params"].get("label", "Nexus Draft Message")

                missing = []
                if not from_email:
                    missing.append("from_email (or DEFAULT_FROM_EMAIL)")
                if not from_label:
                    missing.append("from_label (or DEFAULT_FROM_LABEL)")
                if not reply_to_email:
                    missing.append("reply_to_email (or DEFAULT_REPLY_TO_EMAIL)")

                if missing:
                    if a_id in PENDING_ACTIONS:
                        del PENDING_ACTIONS[a_id]
                    return [
                        TextContent(
                            type="text",
                            text=(
                                "Failed to create campaign draft: missing sender fields: "
                                + ", ".join(missing)
                            ),
                        )
                    ]

                url_campaigns = "https://a.klaviyo.com/api/campaigns/"

                # NOTE: 'campaign-messages' is REQUIRED by the Create Campaign endpoint
                payload_campaign = {
                    "data": {
                        "type": "campaign",
                        "attributes": {
                            "name": campaign_name,
                            "audiences": {"included": [list_id], "excluded": []},
                            "send_strategy": {"method": "immediate"},
                            "campaign-messages": {
                                "data": [
                                    {
                                        "type": "campaign-message",
                                        "attributes": {
                                            "channel": "email",
                                            "label": msg_label,
                                            "content": {
                                                "subject": subject,
                                                "preview_text": preview_text,
                                                "from_email": from_email,
                                                "from_label": from_label,
                                                "reply_to_email": reply_to_email,
                                            },
                                        },
                                    }
                                ]
                            },
                        },
                    }
                }

                resp_c = await client.post(url_campaigns, json=payload_campaign, headers=headers_post)

                if a_id in PENDING_ACTIONS:
                    del PENDING_ACTIONS[a_id]

                if resp_c.status_code not in (200, 201):
                    return [
                        TextContent(
                            type="text",
                            text=(
                                "Failed to create campaign draft.\n"
                                f"Status: {resp_c.status_code}\n"
                                f"Body: {resp_c.text}\n\n"
                                "Tip: Your Klaviyo account may require a configured/verified sending "
                                "address matching from_email."
                            ),
                        )
                    ]

                body = resp_c.json()
                campaign_id = body["data"]["id"]

                message_id = None
                rel = (
                    body["data"]
                    .get("relationships", {})
                    .get("campaign-messages", {})
                    .get("data", [])
                )
                if isinstance(rel, list) and rel:
                    message_id = rel[0].get("id")

                # Best-effort: create + assign a simple HTML template so the email
                # body isn't the Klaviyo placeholder content.
                template_id = None
                template_note = "Template not created."

                if message_id:
                    template_html = (
                        "<!doctype html><html><body style='font-family: Arial, sans-serif;'>"
                        "<p>Hi {{ first_name }},</p>"
                        "<p><strong>VIP early access:</strong> 20% off.</p>"
                        "<p><strong>Use code:</strong> VIP20</p>"
                        "<p><a href='https://example.com/vip'>Shop early access</a></p>"
                        "<p>{% unsubscribe %}</p>"
                        "</body></html>"
                    )
                    template_name = f"{campaign_name} (Nexus Template)"

                    resp_t = await client.post(
                        "https://a.klaviyo.com/api/templates/",
                        json={
                            "data": {
                                "type": "template",
                                "attributes": {
                                    "name": template_name,
                                    "editor_type": "CODE",
                                    "html": template_html,
                                },
                            }
                        },
                        headers=headers_post,
                    )
                    if resp_t.status_code in (200, 201):
                        template_id = resp_t.json()["data"]["id"]
                        template_note = (
                            f"Created template '{template_name}' (template ID: {template_id}).\n"
                            "To apply it: Klaviyo → Campaigns → open this draft → Content "
                            "→ Change template → select the template by name."
                        )
                    else:
                        template_note = (
                            "Template creation failed: "
                            f"{resp_t.status_code} {resp_t.text}"
                        )

                return [
                    TextContent(
                        type="text",
                        text=(
                            f"SUCCESS: Created email campaign draft '{campaign_name}' "
                            f"(campaign ID: {campaign_id}) targeting list {list_id}.\n"
                            + (f"Campaign message ID: {message_id}\n" if message_id else "")
                            + f"{template_note}\n"
                            + "Next: assign a template in Klaviyo before scheduling/sending."
                        ),
                    )
                ]

    raise ValueError(f"Tool {name} not found")