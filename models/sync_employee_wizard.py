# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class SyncEmployeeWizard(models.TransientModel):
    _name = "sync.employee.wizard"
    _description = "Sync Employee information with evaluation"

    

    employee_id = fields.Many2one('hr.employee', string="Employee")
    period_id = fields.Many2one('evaluation.period', string="Period", required=True)


    @api.multi
    def sync_evaluation(self):
        if self.employee_id:
            employee = self.env['hr.employee'].search([('id', '=',self.employee_id.id)])
            manager_id = employee.timesheet_approver.id
            lm_id= employee.line_manager.id
            second_lm_id = employee.line_manager.line_manager.id
            evaluation = self.env['evaluation.evaluation'].search([('period_id', '=',self.period_id.id),('employee_id','=',self.employee_id.id)])
            if evaluation:
                self.env.cr.execute(
                """UPDATE evaluation_evaluation SET manager_id=%s,first_line_manager_id=%s,second_line_manager_id=%s WHERE id=%s""",
                (manager_id, lm_id, second_lm_id, evaluation.id,))
            else:
                raise UserError(_('There is no Evaluation!'))
        if not self.employee_id:
            
            self.env.cr.execute("""select id,employee_id from evaluation_evaluation where period_id=%s """, (self.period_id.id,))
            for items in self.env.cr.dictfetchall():
                try:
                    eval_id = items['id']
                    employee_id = items['employee_id']
                    self.env.cr.execute("""select line_manager,timesheet_approver from hr_employee where id=%s """, (employee_id,))
                    result = self.env.cr.dictfetchall()
                    self.env.cr.execute("""select line_manager from hr_employee where id=%s """, (result[0]['line_manager'],))
                    second_lm_id = self.env.cr.dictfetchall()[0]['line_manager']
                    # employee = self.env['hr.employee'].search([('id', '=',employee_id)])
                    # manager_id = employee.timesheet_approver.id
                    # lm_id= employee.line_manager.id
                    
                    self.env.cr.execute(
                    """UPDATE evaluation_evaluation SET manager_id=%s,first_line_manager_id=%s,second_line_manager_id=%s  WHERE id=%s""",
                    (result[0]['timesheet_approver'], result[0]['line_manager'], second_lm_id, eval_id,))
                    _logger.info('Successfully sync evaluation :%s', eval_id)
                except :
                    _logger.info('Fail to sync evaluation :%s', eval_id)


        
        return True
    




        