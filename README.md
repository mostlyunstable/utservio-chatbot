# UTservio Customer Chatbot

A premium customer service agent for UTservio.

## Architecture (Phase 1)
- **Frontend**: React + Vite (Port 5173). Glassmorphic UI with simulated typing and booking cards.
- **Backend**: Python + FastAPI (Port 8000). Provides secure routing, validation, rate-limiting, and error handling.
- **LLM**: Cloudflare Worker LLM proxy, accessed securely by the FastAPI backend.

## Getting Started

### 1. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add LLM_API_KEY to .env
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup
```bash
# In the root directory
npm install
npm run dev
```

## Security & Limitations
- The LLM API key is stored strictly on the server-side (`backend/.env`).
- Conversations are tracked via `session_id`, but are currently in-memory/ephemeral (Phase 1).
- Booking cards are visual only; real CRM integrations will arrive in future phases.
