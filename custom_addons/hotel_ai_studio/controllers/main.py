from odoo import http
from odoo.http import request

class AIController(http.Controller):

    @http.route('/ai/chat', type='json', auth='user')
    def ai_chat(self, message):
        ai = request.env['ai.studio.chat'].sudo()
        response = ai.send_message(message, mode='pipeline', history='[]')
        return {"reply": response}
