# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import timedelta, datetime
import calendar
import time


class EvaluationScore(models.Model):
    _name = "evaluation.score"
    _description = "Evaluation Score"

    

    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, readonly=True,states={'draft': [('readonly', False)]},domain=[('state','=','onboard')])
    period_id = fields.Many2one('evaluation.period', string="Period", required=True, readonly=True,states={'draft': [('readonly', False)]})
    value = fields.Float(store=True,string="Score" , readonly=True,states={'draft': [('readonly', False)]})
    state = fields.Selection([
        ('draft', 'Draft'),         
        ('validated', 'Validated'), 
        ('processing', 'Processing'),
        ('done', 'Done')],
        string='Status', default='draft', readonly=True,track_visibility='onchange', copy=False)
    score_type_id = fields.Many2one('evaluation.score.type', string="Score Type", required=True , readonly=True,states={'draft': [('readonly', False)]})


    @api.one
    def send_to_validate(self):
        self.state = 'validated'

    @api.one
    def send_to_process(self):
        self.state = 'processing'

    @api.one
    def send_to_done(self):
        self.state = 'done'

    def _get_name(self):
        res = []
        for emp in self:
            name = emp.employee_id.name
            res.append((emp.period_id.name, name))
        return res


    


    


    




        