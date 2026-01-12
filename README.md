# Klaviyo Nexus

**Marketing Ops, Autopilot.**

## Problem Statement
Marketing operations often require bridging the gap between creative intuition and technical execution. Tasks like building complex segments, drafting campaigns, and analyzing performance involve repetitive navigation of complex UIs and logic builders. Marketers need a way to turn natural language requests into structured, safe, and effective Klaviyo actions without getting bogged down in the mechanics of the platform.

## Solution Overview
**Klaviyo Nexus** is an AI-powered agent designed to be the ultimate "copilot" for your Klaviyo account. It leverages the Model Context Protocol (MCP) design pattern to interpret natural language and orchestrate complex workflows.

**Key Features:**
*   **Natural Language Interface:** Chat with your data. Ask Nexus to "Create a VIP audience" or "Draft a re-engagement campaign," and it understands your intent.
*   **Human-in-the-Loop Safety:** AI never acts alone. Nexus "proposes" actions (like creating a list or sending an email) which generate an interactive approval card in the UI. The action executes only when you click "Approve".
*   **Smart Audiences:** Instantly generate lists and segments with seeded data for testing (e.g., creating a demo VIP list with dummy high-spender profiles).
*   **Campaign Drafting:** Automate the tedious parts of campaign creation, including subject lines, preview text, and template assignment.

## Architecture / Design Decisions

### Tech Stack
*   **Infrastructure:** Docker & Docker Compose.
    *   **Design Choice:** Fully containerized application for consistent development and deployment environments.
*   **Frontend:** [Next.js 14](https://nextjs.org/) (React) with TypeScript.
    *   Styling: Tailwind CSS and [shadcn/ui](https://ui.shadcn.com/) for a modern, accessible aesthetic.
    *   **Design Choice:** The chat interface mimics a coding IDE/terminal ("Nexus Agent") to emphasize the "infrastructure as code" nature of the tool, while maintaining a user-friendly conversational flow.
*   **Backend:** [FastAPI](https://fastapi.tiangolo.com/) (Python).
    *   **Design Choice:** Chosen for its speed and native support for asynchronous operations, which is crucial for handling AI streaming and concurrent API calls.
*   **AI Engine:** OpenAI (GPT-4 Turbo).
    *   **Design Choice:** We use function calling (Tools) to structure the AI's output into predictable JSON payloads that the backend can validate and execute.

### Data Flow & Safety
1.  **User Request:** User types a command in the frontend.
2.  **Intent Analysis:** The backend sends the history + available tools to OpenAI.
3.  **Proposal:** If the AI decides to modify data (write operation), it returns a `propose_action` tool call.
4.  **Approval UI:** The frontend renders this proposal as an interactive "Approval Card."
5.  **Execution:** Upon user approval, a second request is sent to the backend to actually call the Klaviyo API (`execute_action`).

## Klaviyo API / SDK / MCP Usage

This project interacts directly with the **Klaviyo API** using raw HTTP requests (via `httpx`) to demonstrate low-level control and understanding of the API endpoints.

**Key Endpoints Used:**
*   **Lists & Segments:**
    *   `GET /api/lists/` & `GET /api/segments/`: To retrieve context about existing audiences.
    *   `POST /api/lists/`: To create new containers for audiences.
*   **Profiles:**
    *   `POST /api/profiles/`: Used to seed "VIP" lists with demo profiles containing custom properties (e.g., `nexus_demo_spend_90d`).
    *   `POST /api/lists/{id}/relationships/profiles/`: To add these profiles to specific lists.
*   **Campaigns:**
    *   `GET /api/campaigns/`: To fetch recent campaign status.
    *   `POST /api/campaigns/`: To draft new email campaigns with specific audiences and send strategies.
*   **Templates:**
    *   `POST /api/templates/`: To dynamically generate HTML templates and assign them to campaign drafts.

## Getting Started / Setup Instructions

### Prerequisites
*   Docker & Docker Compose
*   An OpenAI API Key
*   Klaviyo project setup with client id / secret for auth

### 1. Clone the Repository
```bash
git clone <repo-url>
cd klaviyo-nexus
```

### 2. Environment Setup
Create a `.env` file in the `backend/` directory with the following variables:
```bash
# backend/.env
OPENAI_API_KEY=sk-...
```

### 3. Run with Docker
The entire application (Frontend + Backend) is containerized.
```bash
docker compose up --build
```

*   **Frontend:** Accessible at `http://localhost:3000`
*   **Backend:** Accessible at `http://localhost:8000`

### Manual Setup (Optional)
If you prefer running without Docker:

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Demo

1.  **Open the App:** Navigate to `http://localhost:3000`.
2.  **Connect:** Click "Connect Klaviyo"
3.  **Create an Audience:**
    *   *Type:* "Create a VIP audience for customers who spent over $300."
    *   *Action:* Nexus will propose creating a list named "VIP Audience (demo): $300+".
    *   *Approve:* Click the "Approve" button. Nexus will create the list and seed it with dummy profiles.
4.  **Draft a Campaign:**
    *   *Type:* "Draft a campaign for this new VIP list offering 20% off."
    *   *Action:* Nexus will propose a campaign draft with a subject line like "A special offer for you".
    *   *Approve:* Click "Approve". Nexus will create the campaign and even generate a basic HTML template for it.

## Testing / Error Handling

*   **API Hardening:** The `tools.py` module includes specific error handling for Klaviyo API responses (e.g., 401 Unauthorized, 403 Forbidden).
*   **Timeouts:** Async HTTP calls use explicit timeouts to prevent the agent from hanging indefinitely.
*   **Fallback Logic:** If a specific parameter (like `from_email`) is missing, the system attempts to use environment defaults or prompts the user, preventing crash loops.

## Future Improvements

*   **Real OAuth Flow:** Fully implement the OAuth handshake to allow any Klaviyo user to securely connect their account.
*   **RAG Integration:** Ingest Klaviyo Help Center docs so the agent can answer "How-to" questions in addition to performing actions.
*   **Advanced Analytics:** Use the Reporting API to generate visual charts (e.g., revenue over time) directly in the chat interface.
