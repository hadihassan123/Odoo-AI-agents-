import json
import logging
import os
from pathlib import Path
import re
import urllib.error
import urllib.request

import requests
from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class AiStudioChat(models.TransientModel):
    _name = 'ai.studio.chat'
    _description = 'AI Studio Chat'

    message = fields.Text(string='Message')
    response = fields.Text(string='Response')
    chat_mode = fields.Selection([
        ('groq', 'Groq'),
        ('pipeline', 'Pipeline'),
        ('hotel_data', 'Hotel Data'),
        ('slave','Slave'),
    ], string='Mode', default='groq')
    history = fields.Text(string='History', default='[]')
    chat_history = fields.Html(string="Chat History")
    slave_step = fields.Integer(string='Slave Step', default=0)
    slave_data = fields.Text(string='Slave Data', default='{}')

    def _get_external_backend_config(self):
        params = self.env['ir.config_parameter'].sudo()
        return {
            'url': (params.get_param('ai_studio_backend_url') or '').strip().rstrip('/'),
            'api_key': (params.get_param('ai_studio_backend_api_key') or '').strip(),
            'timeout': float(params.get_param('ai_studio_backend_timeout') or 60),
        }

    def _call_external_backend(self, message, mode, history):
        config = self._get_external_backend_config()
        if not config['url']:
            return None

        if isinstance(history, str):
            history_list = json.loads(history) if history else []
        else:
            history_list = history or []

        headers = {'Content-Type': 'application/json'}
        if config['api_key']:
            headers['X-API-Key'] = config['api_key']

        payload = {
            'message': message,
            'history': history_list[-20:],
        }

        if mode == 'pipeline':
            payload.update({
                'model': 'groq',
                'mode': 'pipeline',
                'session_id': f'odoo-pipeline-{self.env.user.id}',
                'user_id': str(self.env.user.id),
                'metadata': {'source': 'odoo19', 'mode': mode},
            })
            endpoint = '/api/v1/chat'
        elif mode == 'hotel_data':
            payload.update({
                'model': 'groq',
                'mode': 'knowledge',
                'session_id': f'odoo-hotel-data-{self.env.user.id}',
                'user_id': str(self.env.user.id),
                'context': self._get_hotel_context(),
                'metadata': {'source': 'odoo19', 'mode': mode},
            })
            endpoint = '/api/v1/chat'
        else:
            payload.update({
                'model': 'groq',
                'mode': 'general',
                'session_id': f'odoo-general-{self.env.user.id}',
                'user_id': str(self.env.user.id),
                'metadata': {'source': 'odoo19', 'mode': mode},
            })
            endpoint = '/api/v1/chat'

        try:
            response = requests.post(
                f"{config['url']}{endpoint}",
                headers=headers,
                json=payload,
                timeout=config['timeout'],
            )
            response.raise_for_status()
            body = response.json()
        except requests.RequestException as err:
            raise UserError(f'External AI backend request failed: {err}')
        except ValueError as err:
            raise UserError(f'External AI backend returned invalid JSON: {err}')

        if 'response' not in body:
            raise UserError(f'External AI backend returned unexpected payload: {body}')

        return body['response']

    def _get_generated_modules_root(self):
        # Resolve against the current addon so generated modules land in this repo's custom_addons.
        return Path(__file__).resolve().parents[2]

    def _sanitize_generated_rel_path(self, rel_path):
        cleaned = (rel_path or '').strip().replace('\\', '/')
        if not cleaned:
            raise UserError('The AI returned an empty file path.')
        rel = Path(cleaned)
        if rel.is_absolute() or '..' in rel.parts:
            raise UserError(f'Unsafe generated file path: {cleaned}')
        return rel

    def _ask_groq(self, messages):
        key = self.env['ir.config_parameter'].sudo().get_param('groq_api_key') or os.environ.get('GROQ_API_KEY')
        if not key:
            raise UserError('GROQ_API_KEY is not configured. Set it in System Parameters.')
        data = json.dumps({
            'model': 'llama-3.3-70b-versatile',
            'messages': messages
        }).encode()
        req = urllib.request.Request(
            'https://api.groq.com/openai/v1/chat/completions',
            data=data,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {key}',
                'User-Agent': 'python-urllib/3.12'
            }
        )
        try:
            with urllib.request.urlopen(req) as r:
                return json.load(r)['choices'][0]['message']['content']
        except urllib.error.HTTPError as err:
            details = ""
            try:
                body = err.read()
                if body:
                    parsed = json.loads(body.decode("utf-8", errors="ignore"))
                    details = parsed.get("error", {}).get("message", "") or ""
            except Exception:
                details = ""

            if err.code == 401:
                raise UserError(
                    "Groq authentication failed (401 Unauthorized). "
                    "Please verify your GROQ_API_KEY."
                )

            raise UserError(
                f"Groq API request failed with HTTP {err.code}: "
                f"{details or err.reason}"
            )
        except urllib.error.URLError as err:
            raise UserError(f"Network error while contacting Groq API: {err.reason}")

    def _ask_gemma(self, messages):
        key = self.env['ir.config_parameter'].sudo().get_param('openrouter_api_key') or os.environ.get('OPENROUTER_API_KEY')
        try:
            short = [{'role': m['role'], 'content': m['content'][:1000]} for m in messages]
            data = json.dumps({
                'model': 'google/gemma-3n-e4b-it:free',
                'messages': short
            }).encode()
            req = urllib.request.Request(
                'https://openrouter.ai/api/v1/chat/completions',
                data=data,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {key}',
                    'User-Agent': 'python-urllib/3.12'
                }
            )
            with urllib.request.urlopen(req) as r:
                result = json.load(r)
                if 'choices' in result:
                    return result['choices'][0]['message']['content']
        except:
            pass
        return self._ask_groq(messages)

    def _get_hotel_context(self):
        context = "Current hotel data:\n"
        try:
            rooms = self.env['hotel.room'].search([])
            available = self.env['hotel.room'].search([('status', '=', 'available')])
            context += f"Total rooms: {len(rooms)}, Available: {len(available)}\n"
        except:
            context += "No hotel room data found.\n"
        return context

    @api.model
    def send_message(self, message, mode, history):
        try:
            external_response = self._call_external_backend(message, mode, history)
        except UserError as err:
            _logger.warning("AI Studio external backend failed for mode %s: %s", mode, err)
            external_response = None
        if external_response is not None:
            return f"[Standalone backend]\n{external_response}"

        history_list = json.loads(history) if history else []

        if mode == 'hotel_data':
            hotel_context = self._get_hotel_context()
            system_prompt = f"You are an AI assistant for a hotel in Qatar. Hotel data:\n{hotel_context}\nAnswer questions about the hotel."
        elif mode == 'pipeline':
            system_prompt = "You are a senior Odoo 19 developer. Help with code generation, debugging, and module development."
        else:
         system_prompt = "You are a helpful AI assistant for Odoo hotel management."

        messages = [{'role': 'system', 'content': system_prompt}]
        messages.extend(history_list)
        messages.append({'role': 'user', 'content': message})

        if mode == 'pipeline':
            code = self._ask_groq(messages)
            review_messages = [
                {'role': 'system', 'content': 'You are an Odoo 19 code reviewer. Review and suggest improvements.'},
                {'role': 'user', 'content': f'Review:\n{code}'}
            ]
            review = self._ask_gemma(review_messages)
            fix_messages = messages + [
                {'role': 'assistant', 'content': code},
                {'role': 'user', 'content': f'Review:\n{review}\n\nFix the code.'}
            ]
            return f"[Internal fallback]\n{self._ask_groq(fix_messages)}"
        else:
            return f"[Internal fallback]\n{self._ask_groq(messages)}"

    @api.model
    def slave_message(self, message, slave_step, slave_data):
        data = json.loads(slave_data or '{}')
        step = slave_step or 0

        steps = [
            {
                'question': 'What is your module name? (e.g. hotel_accounting)',
                'key': 'module_name'
            },
            {
                'question': 'Give a short description of what this module does.',
                'key': 'description'
            },
            {
                'question': 'What models do you need? (e.g. hotel.room, hotel.folio, hotel.invoice)',
                'key': 'models'
            },
            {
                'question': 'Any dependencies besides base? (e.g. account, sale) — type "no" if none',
                'key': 'dependencies'
            },
            {
                'question': 'Should it have menu items and views? (yes/no)',
                'key': 'has_views'
            },
            {
                'question': 'Should it have security access rules? (yes/no)',
                'key': 'has_security'
            },
        ]

        if step < len(steps):
            data[steps[step]['key']] = message
            next_step = step + 1

            if next_step < len(steps):
                return {
                    'response': steps[next_step]['question'],
                    'slave_step': next_step,
                    'slave_data': json.dumps(data),
                    'done': False
                }
            else:
                # All questions answered — generate module
                deps = data.get('dependencies', 'no')
                if deps.lower() == 'no':
                    deps = 'base'
                else:
                    deps = f"base, {deps}"

                prompt = f"""Generate a complete Odoo 19 module with ALL files.

    Module name: {data.get('module_name')}
    Description: {data.get('description')}
    Models: {data.get('models')}
    Dependencies: {deps}
    Has views: {data.get('has_views')}
    Has security: {data.get('has_security')}

    Generate ALL these files:
    1. __manifest__.py
    2. __init__.py
    3. models/__init__.py
    4. models/[each model].py
    5. views/[module]_views.xml (if has views)
    6. views/[module]_menu.xml (if has views)
    7. security/ir.model.access.csv (if has security)

    Format each file as:
    FILE: relative/path/to/file.ext
    ```
    complete file content here
    ```

    Generate ALL files completely."""

                code = self._ask_groq([
                    {'role': 'system',
                     'content': 'You are a senior Odoo 19 developer. Generate complete working module files.'},
                    {'role': 'user', 'content': prompt}
                ])

                # Save files to custom_addons
                saved_files = []
                module_name = (data.get('module_name') or '').strip()
                if not module_name:
                    raise UserError('Module name is required to generate files.')
                if not re.fullmatch(r'[a-zA-Z0-9_]+', module_name):
                    raise UserError('Module name must contain only letters, numbers, and underscores.')

                base_path = self._get_generated_modules_root() / module_name
                pattern = r"FILE: (.+?)\n```(?:\w+)?\n(.*?)```"
                matches = re.findall(pattern, code, re.DOTALL)

                if matches:
                    base_path.mkdir(parents=True, exist_ok=True)
                    for rel_path, content in matches:
                        safe_rel_path = self._sanitize_generated_rel_path(rel_path)
                        full_path = base_path / safe_rel_path
                        full_path.parent.mkdir(parents=True, exist_ok=True)
                        full_path.write_text(content.strip(), encoding='utf-8')
                        saved_files.append(safe_rel_path.as_posix())

                if saved_files:
                    files_list = '\n'.join([f'✅ {f}' for f in saved_files])
                    response = f"🎉 Module '{module_name}' created successfully!\n\nFiles saved to:\n{base_path}\n\n{files_list}\n\nTo install:\n1. Restart Odoo\n2. Go to Apps → Update App List\n3. Search for '{module_name}' and install"
                else:
                    response = f"Module generated! Here are the files:\n\n{code}\n\n⚠️ Could not save automatically. Copy the files above manually to:\n{base_path}"

                return {
                    'response': response,
                    'slave_step': 0,
                    'slave_data': '{}',
                    'done': True
                }

        return {
            'response': 'Something went wrong. Please try again.',
            'slave_step': 0,
            'slave_data': '{}',
            'done': False
        }

    def action_send(self):
        if not self.message:
            return

        if self.chat_mode == 'slave':
            user_message = self.message

            if user_message.lower() == 'start' and self.slave_step == 0:
                assistant_response = 'What is your module name? (e.g. hotel_accounting)'
                slave_step_val = 0
                slave_data_val = '{}'
            else:
                result = self.slave_message(
                    user_message,
                    self.slave_step,
                    self.slave_data or '{}'
                )
                assistant_response = result['response']
                slave_step_val = result['slave_step']
                slave_data_val = result['slave_data']

            history_list = json.loads(self.history or '[]')
            history_list.append({'role': 'user', 'content': user_message})
            history_list.append({'role': 'assistant', 'content': assistant_response})

            html_history = ""
            for msg in history_list[-20:]:  # Keep the last 20 messages
                if msg['role'] == 'user':
                    html_history += f"""
                        <div class="chat-message user-message" style="margin-bottom: 10px; text-align: right;">
                            <span style="background-color: #714B67; color: white; padding: 8px 12px; border-radius: 15px; display: inline-block; max-width: 70%;">
                                {msg['content']}
                            </span>
                        </div>
                    """
                elif msg['role'] == 'assistant':
                    html_history += f"""
                        <div class="chat-message ai-message" style="margin-bottom: 10px; text-align: left;">
                            <span style="background-color: #e9ecef; color: #333; padding: 8px 12px; border-radius: 15px; display: inline-block; max-width: 70%;">
                                {msg['content']}
                            </span>
                        </div>
                    """

            self.write({
                'response': assistant_response,
                'history': json.dumps(history_list[-20:]),
                'chat_history': html_history,
                'slave_step': slave_step_val,
                'slave_data': slave_data_val,
                'message': '',
            })
            return True

        # 1. Get the response from the AI
        response = self.send_message(
            self.message,
            self.chat_mode,
            self.history or '[]'
        )

        # 2. Update the JSON memory
        history_list = json.loads(self.history or '[]')
        history_list.append({'role': 'user', 'content': self.message})
        history_list.append({'role': 'assistant', 'content': response})

        # 3. Generate HTML for the visual chat box
        html_history = ""
        for msg in history_list[-20:]:  # Keep the last 20 messages
            if msg['role'] == 'user':
                html_history += f"""
                    <div class="chat-message user-message" style="margin-bottom: 10px; text-align: right;">
                        <span style="background-color: #714B67; color: white; padding: 8px 12px; border-radius: 15px; display: inline-block; max-width: 70%;">
                            {msg['content']}
                        </span>
                    </div>
                """
            elif msg['role'] == 'assistant':
                html_history += f"""
                    <div class="chat-message ai-message" style="margin-bottom: 10px; text-align: left;">
                        <span style="background-color: #e9ecef; color: #333; padding: 8px 12px; border-radius: 15px; display: inline-block; max-width: 70%;">
                            {msg['content']}
                        </span>
                    </div>
                """

        # 4. Save everything and clear the input box
        self.write({
            'response': response,
            'history': json.dumps(history_list[-20:]),
            'chat_history': html_history,  # <-- This puts the bubbles in the chat box!
            'message': '',  # <-- This clears the text box so "hi" disappears from the input
        })

        return True  # <-- Prevents the URL Inception loop!
    # def action_send(self):
    #     if not self.message:
    #         return
    #     response = self.send_message(
    #         self.message,
    #         self.chat_mode,
    #         self.history or '[]'
    #     )
    #     history_list = json.loads(self.history or '[]')
    #     history_list.append({'role': 'user', 'content': self.message})
    #     history_list.append({'role': 'assistant', 'content': response})
    #     self.write({
    #         'response': response,
    #         'history': json.dumps(history_list[-20:]),
    #         'message': '',
    #     })
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'ai.studio.chat',
    #         'res_id': self.id,
    #         'view_mode': 'form',
    #         'target': 'current',
    #     }
