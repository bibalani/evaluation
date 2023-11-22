# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import timedelta, datetime
import calendar
import time


class EvaluationPeriod(models.Model):
    _name = "evaluation.period"
    _description = "Evaluation Period"

    name = fields.Char(string='Period Name', required=True , help="Name of evaluation period.")
    date_from = fields.Date(string='From Date', help="Start date of evaluation.")
    date_to = fields.Date(string='To Date', help="End date of evaluation.")
    evaluation_status = fields.Selection(selection=[
        ('normal', ('Normal')),
        ('self_assessment', ('Self Assessment')),
        ('manager_assessment', ('Manager Assessment')),
        ('pause', ('Pause'))], string='Evaluation Status', default='normal')
    is_active = fields.Boolean(string='Active')
    score_type_id = fields.Many2one('evaluation.score.type', string="Score Type", required=True)
    is_pause = fields.Boolean(string='Pause')

    # @api.model
    # def create(self, values):
    #     timesheet_approver_list = self.env.cr.execute("""SELECT DISTINCT manager_id """)


class EvaluationScoreType(models.Model):
    _name = "evaluation.score.type"
    _description = "Evaluation Score Type"


    name = fields.Char(string='Name', required=True , help="Name of score type.")
    is_reward_based = fields.Boolean(string=' Is it for reward base')




        