# Session Notes

## Current setup
- This addon can use the standalone backend through:
  - `ai_studio_backend_url`
  - `ai_studio_backend_api_key`
  - `ai_studio_backend_timeout`
- Standalone backend project:
  - `/home/hadi/PycharmProjects/PythonProject/ai_studio_backend`
- Odoo addon project:
  - `/home/hadi/odoo19/custom_addons/hotel_ai_studio`

## Behavior
- If the backend is up, Odoo uses the standalone backend.
- If the backend is down, Odoo falls back to internal AI logic.
- Temporary visible markers were added for testing:
  - `[Standalone backend]`
  - `[Internal fallback]`

## Backend run
```bash
cd /home/hadi/PycharmProjects/PythonProject/ai_studio_backend
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Next tasks
- Remove the temporary fallback/source labels from Odoo AI Studio responses.
- Run the backend as a background service on the laptop.
- Optionally enable `SERVICE_API_KEY` cleanly.
