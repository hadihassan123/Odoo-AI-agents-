import requests

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request

class AiStudioController(http.Controller):

    @http.route('/ai_studio/send', type='json', auth='user', methods=['POST'])
    def send_message(self, message, mode='groq', history='[]', slave_step=0, slave_data='{}'):
        try:
            if mode == 'slave':
                # Slave flow bootstrap: the first user message should be "start".
                # Then we ask for the module name and keep step=0 until they answer it.
                if isinstance(message, str) and message.lower() == 'start' and (slave_step or 0) == 0:
                    return {
                        'response': 'What is your module name? (e.g. hotel_accounting)',
                        'slave_step': 0,
                        'slave_data': '{}',
                        'done': False,
                    }
                return request.env['ai.studio.chat'].slave_message(
                    message, slave_step, slave_data
                )

            result = request.env['ai.studio.chat'].send_message(
                message, mode, history
            )
            return {'response': result}
        except requests.RequestException as err:
            return {
                'response': f'FastAPI request failed: {err}',
                'slave_step': slave_step or 0,
                'slave_data': slave_data or '{}',
                'done': False,
                'error': True,
            }
        except UserError as err:
            return {
                'response': str(err),
                'slave_step': slave_step or 0,
                'slave_data': slave_data or '{}',
                'done': False,
                'error': True,
            }
        except Exception as err:
            return {
                'response': f'AI Studio error: {err}',
                'slave_step': slave_step or 0,
                'slave_data': slave_data or '{}',
                'done': False,
                'error': True,
            }

    @http.route('/ai_studio', type='http', auth='user', website=False)
    def ai_studio(self):
        return request.render('hotel_ai_studio.ai_studio_page', {})


# from odoo import http
# from odoo.http import request
# import json
#
# class AiStudioController(http.Controller):
#
#     @http.route('/ai_studio/send', type='json', auth='user', methods=['POST'])
#     def send_message(self, message, mode='groq', history='[]'):
#         result = request.env['ai.studio.chat'].send_message(message, mode, history)
#         return {'response': result}
#
#     @http.route('/ai_studio', type='http', auth='user', website=False)
#     def ai_studio(self):
#         return request.render('hotel_ai_studio.ai_studio_page', {})
