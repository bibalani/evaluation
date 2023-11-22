# -*- coding: utf-8 -*-
from typing import List
from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError, UserError
import base64
from base64 import b64encode
from urllib import parse
import http.client
import xmlrpc.client
import ssl
import json

class EvaluationWtaPeriodWeightLine(models.Model):
    _name = 'evaluation.periodic_weight_line'
    
    parent_id = fields.Many2one('evaluation.periodic_weight', string="Parent", readonly=True, copy=False)
    evaluation_period_id = fields.Many2one('evaluation.period', string="Period", required=True, readonly=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, readonly=True)
    value = fields.Float(string="Value")
    analytic_account_id = fields.Many2one('ext.analytic.account', string="Analytic Account", readonly=True)
    project_id = fields.Many2one('ext.analytic.account', string="Project", readonly=True, ondelete='restrict')
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('publish', 'Publish')
        ], 
    string='Status', default='draft', readonly=True, track_visibility='onchange', copy=False )

    analytic_short_name = fields.Char(string="Analytic Short name", related='analytic_account_id.short_name', readonly=True)

    
    def check_evaluation_period(self):
        if self.evaluation_period_id.active != True:
            raise UserError(_('Evaluation period {} is not in active state'.format(self.evaluation_period_id.name)))

    @api.onchange('analytic_account_id')
    def _onchange_analytic_account(self):
        if self.analytic_account_id:
            self.project_id = self.analytic_account_id.parent_id.parent_id.parent_id.id
            
    @api.multi
    def send_to_publish(self):
        for obj in self:
            obj.state = 'publish'


    @api.multi
    def unlink(self):
        for obj in self:
            if obj.state != 'draft':
                raise UserError(_('You Can Only Delete Periodic Weight Line which is in Draft State!'))
        return super(EvaluationWtaPeriodWeightLine, self).unlink()



class EvaluationWtaPeriodWeight(models.Model):
    _name = 'evaluation.periodic_weight'

    name = fields.Char(name="Name", max_length=64, required=True)
    evaluation_period_id = fields.Many2one('evaluation.period', string="Period", required=True, readonly=True)
    employee_ids = fields.Many2many('hr.employee', 'periodic_weight_employee_rel', 'pweight_id', 'emp_id')
    line_ids = fields.One2many('evaluation.periodic_weight_line', 'parent_id', string="Lines", ondelete='restrict')
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('publish', 'Publish')
        ], 
    string='Status', default='draft', readonly=True, track_visibility='onchange', copy=False)


    def send_to_publish(self):
        self.state = 'publish'
        for item in self.line_ids:
            item.send_to_publish()


    def check_evaluation_period(self):
        if not self.evaluation_period_id.is_active:
            raise UserError(_('Evaluation period {} is not in active state'.format(self.evaluation_period_id.name)))

    def get_employees(self):
        #get employees whom not imported for this period
        self.check_evaluation_period()
        self.env.cr.execute("""
        DELETE FROM periodic_weight_employee_rel where pweight_id = {self.id}
        """.format(**locals()))
        self.env.cr.execute("""SELECT id FROM hr_employee WHERE evaluation_enable = True
                            EXCEPT
                            (SELECT emp_id FROM periodic_weight_employee_rel WHERE 
                                pweight_id IN (
                                    SELECT id FROM evaluation_periodic_weight WHERE evaluation_period_id ={}
                                ))""".format(self.evaluation_period_id.id,))
        for emp in self.env.cr.dictfetchall():
            emp_id = emp['id']
            self.env.cr.execute("""
                INSERT INTO periodic_weight_employee_rel(pweight_id, emp_id)
                VALUES({self.id}, {emp_id})
            """.format(**locals()))
        return True
    

    @api.multi
    def unlink(self):
        for obj in self:
            if obj.state != 'draft':
                raise UserError(_('You Can Only Delete Periodic Weight which is in Draft State!'))
        return super(EvaluationWtaPeriodWeight, self).unlink()


    def update_wta_weight(self):
        self.check_evaluation_period()
        emp_without_odooId = ""
        employee_ids = []
        for emp in self.employee_ids:
            employee_ids.append(emp.id)
            if not emp.odoo_id:
                emp_without_odooId += "{emp.name} ({emp.staff_id})\n".format(**locals())
        
        if emp_without_odooId != "":
            raise UserError(_("Following Employee are not synch with ERP Server:\n" + emp_without_odooId))

        perc_weights = self.get_employee_perc_weight(employee_ids, self.evaluation_period_id.date_from, self.evaluation_period_id.date_to)
        self.env.cr.execute("""
        delete from evaluation_periodic_weight_line where parent_id={}
        """.format(self.id))
        for  pw in perc_weights:
            pw_emp_id = pw['employee_id']
            pw_value = pw['perc']
            pw_account_id = pw['account_id']
            project_id = self.env['ext.analytic.account'].browse(pw_account_id).parent_id.parent_id.parent_id.id
            self.env.cr.execute("""
                INSERT INTO evaluation_periodic_weight_line(parent_id, evaluation_period_id, employee_id, value, analytic_account_id, project_id, state)
                VALUES({self.id}, {self.evaluation_period_id.id}, {pw_emp_id},{pw_value}, {pw_account_id}, {project_id}, 'draft')
            """.format(**locals()))

        return True
    
    def get_employee_perc_weight(self, employee_ids, from_date, to_date):
        self.check_evaluation_period()
        from_date = self.evaluation_period_id.date_from.strftime('%Y-%m-%d')
        to_date = self.evaluation_period_id.date_to.strftime('%Y-%m-%d')
        employee_ids += [-1,-2]
        odoo_emp_ids = [-100]
        for emp in self.employee_ids:
            odoo_emp_ids.append(int(emp.odoo_id))

        # server_obj = self.env['remote.server'].search([('name', 'like', 'odoo'), ('disabled', '=', False)])
        # url = "{0}{1}/xmlrpc/object".format(server_obj.host, server_obj.port and ":{0}".format(server_obj.port) or "")

        server = xmlrpc.client.ServerProxy(
            "https://erp.nak-mci.ir/xmlrpc/object"
            ,context=ssl._create_unverified_context()
            )

        db="nak-db-p"
        uid = 1
        password="$irDagh20"
        input = {
        'employee_ids':tuple(odoo_emp_ids),
        'from_date':from_date,
        'to_date':to_date,
        }
        input_str = json.dumps(input)
        erp_result = server.execute_kw(db, uid, password,
            'nak.wta.fina.percentage.line', 'get_wta_perc',
            [1, input_str]
            )


        fetched_aa = [r['account_name'] for r in erp_result]

        emp_mapper = {}
        self.env.cr.execute("""
            SELECT id, odoo_id FROM hr_employee WHERE id in {0}
        """.format(tuple(employee_ids)))
        for emp in self.env.cr.dictfetchall():
            emp_mapper[int(emp['odoo_id'])] = emp['id']

        analytic_mapper = {}
        self.env.cr.execute("""
            SELECT id, short_name FROM ext_analytic_account
        """.format(tuple(employee_ids)))
        for aa in self.env.cr.dictfetchall():
            analytic_mapper[aa['short_name']] = aa['id']
        
        not_exist_aa = [aa for aa in fetched_aa if aa not in analytic_mapper.keys()]

        if not_exist_aa:
            raise UserError(_('Following analytic accounts does not defined in staff: \n'+ str(not_exist_aa)))

        result = []
        for r in erp_result:
            if r['employee_id'] in emp_mapper and r['account_name'] in analytic_mapper:
                result.append(
                    {'perc': r['perc'], 'employee_id':emp_mapper[r['employee_id']] , 'account_id':analytic_mapper[r['account_name']]}
                )

        return result