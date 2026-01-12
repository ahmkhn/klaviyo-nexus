# Klaviyo Nexus

**Marketing Ops, Autopilot.**  
Turn natural language into **safe, structured Klaviyo actions** with human approval + execution trace.

Demo (5 min):  
[![Demo Link](https://img.youtube.com/vi/KdCY2jwBZ0Q/0.jpg)](https://www.youtube.com/watch?v=KdCY2jwBZ0Q)

---

## Why this exists (Problem)

Klaviyo is powerful, but common marketing ops tasks—building audiences, drafting campaigns, and validating settings—often require many UI steps and deep platform knowledge. Beginners get stuck, and experienced teams lose time repeating the same workflows.

**Goal:** make Klaviyo easier to operate by translating “marketing intent” into the correct, safe API operations—without hiding what’s happening.

---

## What Nexus does (Solution)

**Klaviyo Nexus** is an AI-powered Marketing Operations Agent that converts natural language requests into structured Klaviyo actions using an MCP-style tool layer.

### Key features
- **Natural language → structured actions**
  - Example: “Create a VIP audience for customers who spent over $300 and draft an email campaign for them.”
- **Human-in-the-loop safety**
  - Nexus never performs write actions immediately. It first returns a proposal and waits for **Approve & Create**.
- **Execution trace**
  - Every tool call is shown to the user (inputs + outputs) for transparency and debugging.
- **VIP audience recipe (demo-mode, works on fresh accounts)**
  - Creates a VIP **list** and seeds demo profiles with properties like:
    - `nexus_demo_spend_90d`
    - `nexus_demo_is_vip`
- **Campaign draft creation**
  - Creates an **email campaign draft** targeting the VIP list (subject/sender fields included).

### Safety guarantees (important)
- **No silent writes:** everything is approval-gated.
- **No sending:** Nexus creates drafts only; it does not schedule or send campaigns.
- **Demo profiles are synthetic:** seeded emails use `example.com`.

---

## Architecture (high-level)

Frontend (Next.js) → Backend (FastAPI) → AI (OpenAI Tools) → Klaviyo API (OAuth)

1. User types a request in chat
2. Model selects a tool call (`propose_action`)
3. UI renders an approval card
4. On approval, backend executes (`execute_action`) against Klaviyo APIs
5. UI shows execution trace + created resource IDs

---

## Klaviyo API usage (meaningful integration)

This project uses Klaviyo’s API directly via `httpx` (raw JSON:API requests) to demonstrate correct, low-level control.

### Endpoints used
**Accounts**
- `GET /api/accounts/`

**Lists**
- `GET /api/lists/`
- `POST /api/lists/`
- `POST /api/lists/{id}/relationships/profiles/` (attach seeded profiles)

**Profiles**
- `POST /api/profiles/` (seed demo profiles)

**Campaigns**
- `GET /api/campaigns/?filter=equals(messages.channel,'email')`
- `POST /api/campaigns/` (create email campaign draft + campaign message)

**Templates (optional)**
- `POST /api/templates/` (create HTML template)
  - Note: auto-assigning templates to campaign messages is currently a known limitation due to method/relationship differences by API revision; manual attach works in the UI.

---

## Setup / Run locally

### Prerequisites
- Docker + Docker Compose
- OpenAI API key
- A Klaviyo account with an OAuth app (Client ID/Secret)
- A configured sender identity in Klaviyo (required to create email campaign drafts)

### Environment variables

Create `backend/.env`:

```bash
OPENAI_API_KEY=sk-...

# Klaviyo OAuth (example names; match your backend)
KLAVIYO_CLIENT_ID=...
KLAVIYO_CLIENT_SECRET=...
KLAVIYO_REDIRECT_URI=http://localhost:8000/api/oauth/callback
```

### Run with Docker

```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000

---

## Required Klaviyo OAuth scopes

Your OAuth app should request the minimum scopes needed for the demo:

- `accounts:read`
- `lists:read`, `lists:write`
- `profiles:write` (needed for demo seeding)
- `campaigns:write`, `campaigns:read`
- (optional) `templates:write`, `templates:read`

If any write scope is missing, Nexus will still run read actions, but creation steps may fail with 403.

---

## Demo (copy/paste prompts)

### 1) Create VIP audience (demo seed)
Prompt:
> Create a VIP audience for customers who spent at least $300. Seed 3 demo VIP profiles.

Then click **Approve & Create**.

Verification in Klaviyo UI:
- Go to **Profiles**
- Search one seeded email printed in the trace (e.g., `vip.user1.1234@example.com`)
- Open profile and confirm:
  - `nexus_demo_spend_90d`
  - `nexus_demo_is_vip`
  - List membership includes your VIP list

### 2) Create a campaign draft for that VIP list
Prompt:
> Create a draft email campaign called “VIP Early Access” for the VIP list we just created. Subject: “VIP Early Access: 20% off”.

Then click **Approve & Create**.

Verification in Klaviyo UI:
- Go to **Campaigns**
- Open the draft and confirm subject/sender fields are populated.

---

## Troubleshooting

- **I don’t see seeded profiles immediately**
  - Klaviyo UI can take ~30–60 seconds to reflect new profiles. Refresh and search again.
- **Campaign draft creation fails**
  - Ensure you have a sender identity configured in Klaviyo and the OAuth token includes `campaigns:write`.
- **403 errors**
  - Confirm your OAuth scopes include the required permissions (Profiles write is needed for seeding).

---

## Testing / reliability notes

- Async requests use timeouts to prevent hanging.
- Tool inputs are schema-restricted (`additionalProperties: false`) to reduce accidental or unsafe tool execution.
- All write actions are approval-gated.

(Short-term improvement: add small mocked tests around propose/execute approval logic.)

---

## Future improvements

- **Segments (real “recipe → segment” builder):** implement VIP/Winback segments on accounts with ecommerce events.
- **Template auto-assignment:** resolve the correct relationship method/path for the chosen API revision and attach templates programmatically.
- **Reporting dashboards:** integrate Reporting API (campaign + flow performance over time).
- **More recipes:** Winback, browse abandonment, post-purchase cross-sell.
- **Hardening:** persistent storage for approvals + trace (Redis/DB), idempotency keys, rate-limit handling.
