# WP4 Employer Agent

Conversational employer job-post drafting in French and Tunisian Derja. The service collects answers, preserves skipped fields as unknown, and validates completed output with WP1's `NormalizedJobOffer` contract.

## Local setup

From the repository root, install the work packages into the active environment:

```powershell
cd backend
python -m pip install -r requirements.txt
```

Set the model endpoint in `backend/.env` (or the process environment):

```dotenv
LLM_BASE_URL=http://localhost:1234/v1
LLM_MODEL=your-loaded-lm-studio-model-id
LLM_API_KEY=lm-studio
LLM_TIMEOUT_SECONDS=60
```

To test LM Studio's native REST endpoint directly, run:

```bash
curl http://localhost:1234/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen/qwen3.5-9b",
    "system_prompt": "You answer only in rhymes.",
    "input": "What is your favorite color?"
  }'
```

This direct smoke test uses LM Studio's native `/api/v1/chat` API. The WP4 application currently uses the OpenAI-compatible `/v1/chat/completions` endpoint configured by `LLM_BASE_URL`.

Start LM Studio's local server with the model loaded, then run the backend:

```powershell
cd backend
python -m uvicorn app.main:app --reload
```

Sign in through the existing employer API and open `http://127.0.0.1:8000/employer-agent/`. The conversational routes are under `/employer-agent/sessions`. Draft sessions are stored in `employer_draft_sessions`; apply the Supabase migration before using the production database.

The LLM model identifier depends on the model loaded in LM Studio. The default `local-model` is only a placeholder, so set `LLM_MODEL` before starting the application. Sample generation inputs for retail, software, customer support, and seasonal work are in `evals/job_types.json`.

Offer generation also requires validated skills in WP1's database; without them, answers remain saved but no offer is emitted.
