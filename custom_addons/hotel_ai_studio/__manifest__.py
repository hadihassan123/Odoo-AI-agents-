
{
    'name': 'Hotel AI Studio',
    'version': '19.0.1.0.0',
    'category': 'Hotel',
    'summary': 'AI Assistant for Hotel Management',
    'description': 'Integrated AI Studio with Groq and Gemma for hotel operations',
    'author': 'Hadi',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/ai_studio_views.xml',
        'views/ai_studio_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hotel_ai_studio/static/src/css/ai_studio.css',
            'hotel_ai_studio/static/src/css/ai_chat.css',
            'hotel_ai_studio/static/src/js/ai_studio.js',
        ],
    },
    'installable': True,
    'application': True,
}



# {
#     'name': 'Hotel AI Studio',
#     'version': '19.0.1.0.0',
#     'category': 'Hotel',
#     'summary': 'AI Assistant for Hotel Management',
#     'description': 'Integrated AI Studio with Groq and Gemma for hotel operations',
#     'author': 'Hadi',
#     'depends': ['base', 'web'],
#     'data': [
#         'security/ir.model.access.csv',
#         'views/ai_studio_views.xml',
#         'views/ai_studio_menu.xml',
#     ],
#     'assets': {
#         'web.assets_backend': [
#             'hotel_ai_studio/static/src/css/ai_studio.css',
#             'hotel_ai_studio/static/src/js/ai_studio.js',
#         ],
#     },
#     'installable': True,
#     'application': True,
# }
