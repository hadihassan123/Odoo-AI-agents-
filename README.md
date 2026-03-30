# AI Studio Backend

Standalone FastAPI service for AI Studio so Odoo 19 can call it over HTTP instead of embedding the AI code inside `custom_addons`.

## What it provides

- `POST /api/v1/chat`
- `GET /api/v1/chat/history`
- `GET /health`
- `POST /ai/chat` for old Odoo widget compatibility
- `POST /ai_studio/send` for old AI Studio controller compatibility

The service stores chat records in SQLite by default and can be switched to PostgreSQL by setting `DATABASE_URL`.
If `SERVICE_API_KEY` is set, chat endpoints require `X-API-Key`.

## Local run

1. Create an env file:

```bash
cp .env.example .env
```

2. Set at least one provider key in `.env`:

- `GROQ_API_KEY`
- `OPENROUTER_API_KEY`

Also set:

- `SERVICE_API_KEY` for requests coming from Odoo

3. Install dependencies and run:

```bash
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

You can also use the settings from `.env` directly:

```bash
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## Odoo 19 integration

Configure your Odoo addon to call:

- Base URL: `http://127.0.0.1:8000`
- Health: `GET /health`
- Chat: `POST /api/v1/chat`
- Header: `X-API-Key: <SERVICE_API_KEY>`

Legacy Odoo-compatible routes also exist:

- `POST /ai/chat` returns `{"reply": "..."}`
- `POST /ai_studio/send` returns `{"response": "..."}`

These match the current controller response shapes in your Odoo addon, but Odoo will not use them automatically unless you reroute or update the Odoo side to send requests here.

Example request body:

```json
{
  "message": "Summarize this sales order issue",
  "model": "groq",
  "mode": "general",
  "session_id": "odoo-user-42",
  "user_id": "42",
  "context": "Optional Odoo business context",
  "metadata": {
    "source": "odoo19",
    "model_name": "sale.order"
  },
  "history": [
    {"role": "user", "content": "Earlier prompt"},
    {"role": "assistant", "content": "Earlier reply"}
  ]
}
```

Example response:

```json
{
  "id": 1,
  "response": "AI response text",
  "session_id": "odoo-user-42",
  "user_id": "42",
  "model": "groq",
  "mode": "general"
}
```

Minimal Odoo-side Python request shape:

```python
import requests

response = requests.post(
    "http://127.0.0.1:8000/api/v1/chat",
    headers={"X-API-Key": "your-shared-key"},
    json={
        "message": prompt,
        "model": "groq",
        "mode": "general",
        "session_id": f"odoo-user-{user_id}",
        "user_id": str(user_id),
        "context": business_context,
        "history": history,
    },
    timeout=60,
)
response.raise_for_status()
payload = response.json()
answer = payload["response"]
```

## Important integration constraint

Your current Odoo code does not call an external backend. It serves `/ai/chat` inside Odoo and then calls `request.env['ai.studio']` and `request.env['ai.studio.chat']` directly.

That means this backend can be made compatible, but Odoo will not start using it until one of these happens:

1. You change the Odoo addon to call this backend over HTTP.
2. You place a reverse proxy in front of Odoo and route `/ai/chat` or `/ai_studio/send` away from Odoo to this backend.
3. You disable the Odoo controller and expose this backend to the frontend under the same path through your local web stack.

Without one of those manual steps, zero Odoo-code changes is not technically possible.

## Production notes

- Bind to `127.0.0.1` if only local Odoo should access it.
- Use PostgreSQL instead of SQLite if you expect concurrent writes or multiple users.
- Disable docs in production with `ENABLE_DOCS=false`.
- Restrict `CORS_ORIGINS` to the Odoo host you actually use.
- Set a strong `SERVICE_API_KEY` before wiring Odoo to this service.
