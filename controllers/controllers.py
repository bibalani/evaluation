# -*- coding: utf-8 -*-
from odoo import http

# class Evaluation(http.Controller):
#     @http.route('/evaluation/evaluation/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/evaluation/evaluation/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('evaluation.listing', {
#             'root': '/evaluation/evaluation',
#             'objects': http.request.env['evaluation.evaluation'].search([]),
#         })

#     @http.route('/evaluation/evaluation/objects/<model("evaluation.evaluation"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('evaluation.object', {
#             'object': obj
#         })



# class EvaluationPeriod(http.Controller):
#     @http.route('/evaluation/evaluation_period/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/evaluation/evaluation_period/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('evaluation.period.listing', {
#             'root': '/evaluation/evaluation_period',
#             'objects': http.request.env['evaluation.period'].search([]),
#         })

#     @http.route('/evaluation/evaluation_period/objects/<model("evaluation.period"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('evaluation.period.object', {
#             'object': obj
#         })