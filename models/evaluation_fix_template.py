# -*- coding: utf-8 -*-
from odoo import api, fields, models,_
from lxml import etree
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning




# class EvaluationFixObjectives(models.Model):
#     _name = "evaluation.fix.objectives"
#     _inherit = ['mail.thread']
#     _description = "Evaluation Fix Objectives"



#     name = fields.Char(string='Name', required=True , help="Name of evaluation fix objective."
#         , readonly=True, states={'new': [('readonly', False)]})
    
#     state = fields.Selection([
#         ('new', 'New'),         
#         ('running', 'Running'), 
#         ('closed', 'Closed')],
#         string='Status', default='new', readonly=True,track_visibility='onchange', copy=False)
#     type_of_category_item = fields.Many2one('evaluation.category.items', string="Category Item", 
#         required=True,track_visibility='onchange', readonly=True,states={'new': [('readonly', False)]})#, ondelete='cascade'
#     function_name = fields.Char(string="Function Name", readonly=True, states={'new': [('readonly', False)]})




#     @api.multi
#     def unlink(self):
#         if self.state in ('running','closed'):
#             raise UserError(_('Cannot delete Objective in %s state!')%(self.state))
#         return super(EvaluationFixObjectives, self).unlink()

#     @api.one
#     def send_to_running(self):
#         self.state = 'running'

#     @api.one
#     def send_to_close(self):
#         self.state = 'closed'


class EvaluationFixTemplate(models.Model):
    _name = "evaluation.fix.template"
    _description = "Evaluation Fix Template"
    _inherit = ['mail.thread']



   
    name = fields.Char(string='Name', required=True, help="Name of Fix Template.", readonly=True, states={'new': [('readonly', False)]})
    state = fields.Selection([
        ('new', 'New'),         
        ('running', 'Running'), 
        ('closed', 'Closed')],
        string='Status', default='new', readonly=True, track_visibility='onchange', copy=False)
    fix_objective_items = fields.One2many('evaluation.fix.template.items' ,'fix_tmp_id',string="Objective Items", readonly=True, states={'new': [('readonly', False)]}, copy=True)
    category_id = fields.Many2one('evaluation.category', string="Category Name", readonly=True, states={'new': [('readonly', False)]}, required=True)


    @api.multi
    def unlink(self):
        if self.state in ('running','closed'):
            raise UserError(_('Cannot delete Template in %s state!')%(self.state))
        return super(EvaluationFixTemplate, self).unlink()

  
    @api.multi
    def send_to_running(self):
        item_categories = []
        for item in self.fix_objective_items:
            item_categories.append(item.category_id.category_id.id)
        
        item_categories = list(set(item_categories))
        if len(item_categories) > 1:
            raise ValidationError(_("All Items have to be in same category!"))
        if len(item_categories) < 1:
            raise ValidationError(_("No Item added!"))
        self.category_id = item_categories[0]
        self.state = 'running'


    @api.one
    def send_to_close(self):
        # onboard_emp_using_templ = self.env['hr.employee'].search([('state', '=', 'onboard'), ('evaluation_fix_template_id', '=', self.id)])
        # if len(onboard_emp_using_templ) > 0:
        #     raise UserError(_('There are employees whom use this template!'))
        self.state = 'closed'
        

class EvaluationFixTemplateItems(models.Model):
    _name = "evaluation.fix.template.items"
    _description = "Evaluation Template Fix Items"



    # @api.model
    # def _default_main_categ(self):
    #     categ = self.fix_tmp_id.category_id
    #     fix_template_id = self.env.context.get('params')['id']
    #     fix_template_obj = self.env['evaluation.fix.template'].browse(fix_template_id)
    #     print("\n\nDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD\n\n")
    #     print(categ)
    #     print(fix_template_obj)
    #     print(self.env.context)
    #     print("\n\nDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD\n\n")
    #     return fix_template_obj.category_id


    category_id = fields.Many2one('evaluation.category.items', string="Category Name",domain=[('is_active','=',True)],  required=True)
    # fix_obj_item = fields.Many2one('evaluation.fix.objectives', string="Objective Name",required=True)

    objective_item_id = fields.Many2one('evaluation.objectives', string="Objective Name",
        domain=[('state', '=','running'),('type_of_category_item','=','category_id'), ('is_fix', '=', True)])
    objective_function = fields.Text(string="Objective Function", related="objective_item_id.function_name")
    # obj_item = fields.Many2one('evaluation.objectives', string="Objective Name",  required=True,domain=[('state', '=','running'),('type_of_category_item','=','category_id'), ('is_fix', '=', False)])
    fix_tmp_id = fields.Many2one('evaluation.fix.template', string="Fix Template Name",  required=True)
    weight = fields.Float(string="Weight")
    target = fields.Float(string="Target")
    description = fields.Text(string="Description")
    # , related="fix_tmp_id.category_id",
    # main_category_id = fields.Many2one('evaluation.category', default=_default_main_categ, readonly=True)

    @api.multi
    @api.onchange('category_id','fix_tmp_id')
    def onchange_category_items(self):
        general_cond = []
        if self.category_id:
            self.obj_item = ''
            general_cond += self.env['evaluation.objectives'].search([('type_of_category_item', '=', self.category_id.id),('state', '=','running'), ('is_fix', '=', True)])
            general_cond = [x.id for x in general_cond]
        return {'domain':{'objective_item_id':[('id', 'in', general_cond)]}}


class Employee(models.Model):
    _inherit = 'hr.employee'


    evaluation_enable = fields.Boolean(string="Evaluation Enable?")


    # evaluation_fix_template_id = fields.Many2one('evaluation.fix.template', string="Eval Fix Template"
    #     ,track_visibility='onchange')



    # @api.multi
    # @api.onchange('evaluation_fix_template_id','evaluation_category')
    # def onchange_category_items(self):
    #     general_cond = []
    #     if self.evaluation_category:
    #         self.obj_item = ''
    #         general_cond += self.env['evaluation.fix.objectives'].search([('type_of_category_item', '=', self.evaluation_category.id),('state', '=','running')])
    #         general_cond = [x.id for x in general_cond]
    #     return {'domain':{'fix_obj_item':[('id', 'in', general_cond)]}}


    # @api.multi
    # def write(self, vals):
    #     res = super(Employee, self).write(vals)
    #     for obj in self:
    #         if obj.evaluation_fix_template_id.category_id.id and obj.evaluation_category.id: 
    #             if obj.evaluation_fix_template_id.category_id.id != obj.evaluation_category.id:
    #                 raise UserError(_('Evaluation Fix Template category have to be same as evaluation category'))

    #     return res


    
    # @api.model
    # def create(self, values):
    #     if 'evaluation_category' in values and values['evaluation_category'] and 'evaluation_fix_template_id' in values and values['evaluation_fix_template_id']:
    #         fix_template_obj = self.env['evaluation.fix.template'].browse(values['evaluation_fix_template_id'])
    #         if values['evaluation_category'] != fix_template_obj.category_id.id:
    #             raise UserError(_('Evaluation Fix Template category have to be same as evaluation category'))
    #     return super(Employee, self).create(values)