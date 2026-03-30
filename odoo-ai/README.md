# odoo-ai

Standalone terminal AI Studio project for Odoo-oriented workflows.

This is separate from the Odoo addon in `custom_addons/hotel_ai_studio`.

## What it is

- Terminal-first project
- Separate `Pipeline`, `Agents`, and `Slave` areas
- Questionnaire-driven module builder

## Run

```bash
cd odoo-ai
python3 -m odoo_ai.main
```

## Current scope

- CLI shell with tab/menu structure
- Module-building questionnaire before generation
- Placeholder handlers for pipeline, agents, and slave flows

## Next step

Wire this CLI to your actual Groq / Gemma / local backend implementation.
