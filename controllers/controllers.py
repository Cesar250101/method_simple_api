# -*- coding: utf-8 -*-
from odoo import http

# class MethodSimpleApi(http.Controller):
#     @http.route('/method_simple_api/method_simple_api/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/method_simple_api/method_simple_api/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('method_simple_api.listing', {
#             'root': '/method_simple_api/method_simple_api',
#             'objects': http.request.env['method_simple_api.method_simple_api'].search([]),
#         })

#     @http.route('/method_simple_api/method_simple_api/objects/<model("method_simple_api.method_simple_api"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('method_simple_api.object', {
#             'object': obj
#         })