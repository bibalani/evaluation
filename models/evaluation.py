# -*- coding: utf-8 -*-

from cmath import nan
import string
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import time

class Evaluation(models.Model):
    _name = 'evaluation.evaluation'
    _description = "Evaluation Form"
    _inherit = ['mail.thread']


    state = fields.Selection([
        ('draft', 'Draft'),         
        # ('waiting_for_emp', 'Waiting For Employee'), 
        ('waiting_for_mng', 'Waiting For Manager'),
        ('waiting_for_general_mng', 'Waiting For General Manager'),
        ('waiting_for_lm', 'Waiting For LM'),
        ('emp_eval', 'Employee Evaluation'),
        ('mng_eval', 'Manager Evaluation'),
        ('emp_review', 'Employee Review'),
        ('claim', 'Claim'),
        ('done', 'Done')],
        string='Status', default='draft', readonly=True,track_visibility='onchange', copy=False)
    name = fields.Char(string='Name',readonly=True, compute='_get_name')
    employee_id = fields.Many2one('hr.employee', string="Employee",  required=True, readonly=True,states={'draft': [('readonly', False)]},domain=[('state','=','onboard')])
    period_id = fields.Many2one('evaluation.period', string="Period", required=True, readonly=True,states={'draft': [('readonly', False)]})#, ondelete='cascade'
    manager_id = fields.Many2one('hr.employee', string="Manager", required=True, compute='_get_name',store=True,readonly=True,domain=[('state','=','onboard')])
    general_manager_id = fields.Many2one('hr.employee', string="General Manager",compute='_get_name', store=True, domain=[('state','=','onboard')])
    first_line_manager_id = fields.Many2one('hr.employee', string="First Line Manager", required=True, compute='_get_name',readonly=True,store=True,domain=[('state','=','onboard')])
    second_line_manager_id = fields.Many2one('hr.employee', string="Second Line Manager", required=False,compute='_get_name',store=True )
    tmp_id = fields.Many2one('evaluation.template', string="Template",readonly=True,states={'draft': [('readonly', False)]},domain="[('id', 'in', domain_tmp_ids)]")
    manager_note = fields.Text('Manager Note')
    general_manager_note = fields.Text('General Manager Note')
    line_manager_note = fields.Text('Line Manager Note')
    ind_total_score = fields.Float(compute="_ind_total_score", store=True,string="Individual Total Score")
    final_score = fields.Float(compute="_manager_score", store=True,string="Final Score")
    total_score = fields.Float(compute="_total_score", string="Total Score")
    organization_score = fields.Float(string="Organization Score", readonly=True)
    manager_sign = fields.Boolean(string='Manager Sign',readonly=True)
    general_manager_sign = fields.Boolean(string='General Manager Sign', readonly=True)
    lm_sign = fields.Boolean(string='LM Sign',readonly=True)
    claim = fields.Boolean(string='Claim',readonly=True)
    obj_items = fields.One2many('evaluation.objectives.items' ,'eval_id',string="Objective Items",readonly=True,states={'draft': [('readonly', False)]})
    eval_items = fields.One2many('evaluation.items' ,'eval_id',string="Evaluation Items",readonly=True,states={'emp_eval': [('readonly', False)]},store=True)
    manager_comment = fields.Text(string="Manager Comment",readonly=True,states={'mng_eval': [('readonly', False)]})
    general_manager_comment = fields.Text(string="General Manager Comment",readonly=True,states={'mng_eval': [('readonly', False)]})
    lm_comment = fields.Text(string="LM Comment",readonly=True,states={'mng_eval': [('readonly', False)]})
    emp_comment = fields.Text(string="Employee Comment",store=True)
    mng_score = fields.Float(compute="_manager_score", store=True,string="Manager Score")
    general_mng_score = fields.Float(string="General Manager Score", compute="_manager_score", store=True,)
    # compute="_manager_score", store=True
    lm_score = fields.Float(compute="_manager_score",string="LM Score", store=True,)
    score_id = fields.Many2one('evaluation.score',string="Score ID",readonly=True)
    evaluation_status = fields.Selection(selection=[
        ('normal', ('Normal')),
        ('self_assessment', ('Self Assessment')),
        ('manager_assessment', ('Manager Assessment')),
        ('pause', ('Pause'))
    ], string='Evaluation Status',compute='_get_period_status')
    check_access_right = fields.Boolean(compute="check_access",string='Access Right',readonly=True)
    check_access_right_manager = fields.Boolean(compute="check_access_mng",string='Access Right Mng',readonly=True)
    check_access_right_general_manager = fields.Boolean(compute="check_access_general_mng",string='Access Right General Mng',readonly=True)
    check_access_right_line = fields.Boolean(compute="check_access_line",string='Access Right LM',readonly=True)
    check_access_right_admin = fields.Boolean(compute="check_access_admin",string='Access Right Admin',readonly=True)

    eval_items_manager = fields.One2many('evaluation.items.manager' ,'eval_id',string="Manager Evaluation Items")
    
    domain_tmp_ids = fields.Many2many('evaluation.template', 'evaluation_template_rel', 'eval_id', 'temp_id', string="Templates",compute='_compute_tmp_id')
    approver_panel_id = fields.Many2one('approver.panel', string="Timesheet Approver Panel", readonly=True, compute='_get_ta_panel')
    general_manager_panel_id = fields.Many2one('general.manager.panel', string="Genearl Manager Panel", readonly=True, compute='_get_gm_panel')
    line_manager_panel_id = fields.Many2one('line.manager.panel', string="Line Manager Panel", readonly=True, compute='_get_lm_panel')
    mng_eval_status = fields.Selection([
        ('draft','Draft'),
        ('manager_signed','Manager Approved'),
        ('edited','Edited'),
        ('rejected', 'Rejected'),
        ('unchanged','Unchanged'),
        ('gm_manager_edited','GM Edited'),
        ('gm_manager_unchanged','GM Unchanged'),
        ('lm_edited','Line Edited'),
        ('lm_unchanged','Line Unchanged'),
        ('line_manager_signed','Line Manager Approved')
    ], string='Manager Evaluation Status', default='draft', readonly=True,)
    second_deviation = fields.Float(string="Deviation (General Manager-Manager)",compute='_calculate_second_deviation', store=True,)
    fourth_deviation = fields.Float(string="Deviation (LM-General Manager)",compute='_calculate_fourth_deviation', store=True,)




    @api.multi
    @api.depends('mng_score','general_mng_score')
    def _calculate_second_deviation(self):
        for rec in self:
            if rec.mng_score != 0:            
                rec.second_deviation = round(abs(rec.general_mng_score - rec.mng_score)/rec.mng_score, 3)
            else:
                rec.second_deviation = 0

    @api.multi
    @api.depends('general_mng_score','lm_score')
    def _calculate_fourth_deviation(self):
        for rec in self:
            if rec.general_mng_score != 0:
                rec.fourth_deviation = round(abs(rec.general_mng_score - rec.lm_score)/rec.general_mng_score, 3)
            else:
                rec.fourth_deviation = 0        

    


      





    @api.one
    @api.depends('period_id','manager_id')
    def _get_ta_panel(self):
        approver_panel_obj = self.env['approver.panel'].search([('timesheet_approver_id','=',self.manager_id.id),('period_id','=',self.period_id.id)])
        if approver_panel_obj:
            self.approver_panel_id = approver_panel_obj[0].id
        # else:
        #     raise UserError(('There is not any approver panel for period %s!') % (self.period_id.name)) 
        # return True     

    @api.one
    @api.depends('period_id','general_manager_id')
    def _get_gm_panel(self):
        general_manager_panel_obj = self.env['general.manager.panel'].search([('general_manager_id','=',self.general_manager_id.id),('period_id','=',self.period_id.id)])
        if general_manager_panel_obj:
            self.general_manager_panel_id = general_manager_panel_obj[0].id
        # else:
        #     raise UserError(('There is not any general manager panel for period %s!') % (self.period_id.name)) 
        # return True  
        # 
        #    
    @api.one
    @api.depends('period_id','first_line_manager_id')
    def _get_lm_panel(self):
        line_manager_panel_obj = self.env['line.manager.panel'].search([('first_line_manager_id','=',self.first_line_manager_id.id),('period_id','=',self.period_id.id)])
        if line_manager_panel_obj:
            self.line_manager_panel_id = line_manager_panel_obj[0].id
        # else:
        #     raise UserError(('There is not any general manager panel for period %s!') % (self.period_id.name)) 
        # return True     


    def open_one2many_line(self):
        return {
                    'type': 'ir.actions.act_window',
                    'name': 'Evaluation Form',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': self._name,
                    'res_id': self.id,
                    'target': 'current',
                    }



    @api.multi
    @api.onchange('employee_id')
    def onchange_employee_id(self):
        if self.employee_id and (not self.employee_id.evaluation_category):
            raise UserError(_('No evaluation category defined in your HR profile!'))

    # domain for tmp_id is set through onchange_template_id and _compute_tmp_id!         
    @api.multi
    @api.onchange('employee_id')
    def onchange_template_id(self):
        filtered_template = []
        general_cond = []
        spcific_cond = []
        if self.employee_id:
            self.tmp_id = ''   
            general_cond += self.env['evaluation.template'].search([('state', '=','running'),('lm_name', '=',self.first_line_manager_id.id),('manager_name', '=', False)])
            spcific_cond += self.env['evaluation.template'].search([('state', '=','running'),('lm_name', '=',self.first_line_manager_id.id),('manager_name', '=', self.manager_id.id)])
            general_cond = [x.id for x in general_cond]
            spcific_cond = [x.id for x in spcific_cond]
            filtered_template = list(set(general_cond).union(spcific_cond))
            evaluation_category = self.employee_id.evaluation_category
            fix_templates = self.env['evaluation.fix.template'].search([('category_id', '=', evaluation_category.id), ('state', '=', 'running')])
            fix_items = []
            if fix_templates:
                fix_template = fix_templates[0]
                for fix_item in fix_template.fix_objective_items:
                    fix_items.append((0, 0, {
                        'category_id':fix_item.category_id.id,
                        'obj_item':fix_item.objective_item_id.id,
                        # 'eval_id':self.id,
                        'weight':fix_item.weight,
                        'target': fix_item.target,
                        'description': fix_item.description,
                        'is_fix':True,
                    }))
            self.obj_items = fix_items
        return {'domain':{'tmp_id':[('id', 'in', filtered_template)]}}


    def _compute_tmp_id(self):

        filtered_template = []
        general_cond = []
        spcific_cond = []
        if self.employee_id:
            # self.tmp_id = ''   
            general_cond += self.env['evaluation.template'].search([('state', '=','running'),('lm_name', '=',self.first_line_manager_id.id),('manager_name', '=', False)])
            spcific_cond += self.env['evaluation.template'].search([('state', '=','running'),('lm_name', '=',self.first_line_manager_id.id),('manager_name', '=', self.manager_id.id)])
            general_cond = [x.id for x in general_cond]
            spcific_cond = [x.id for x in spcific_cond]
            filtered_template = list(set(general_cond).union(spcific_cond))
            self.domain_tmp_ids = filtered_template

    @api.one
    @api.depends('employee_id')
    def check_access(self):
        if self.employee_id.user_id.id == self._uid or self.user_has_groups("ext_evaluation.group_see_all_evaluation"):
            self.check_access_right = True
        else:
            self.check_access_right = False

    @api.one
    @api.depends('manager_id')
    def check_access_mng(self):
        if self.manager_id.user_id.id == self._uid:
            self.check_access_right_manager = True
        else:
            self.check_access_right_manager = False

    @api.one        
    @api.depends('general_manager_id')
    def check_access_general_mng(self):
        if self.general_manager_id.user_id.id == self._uid:
            self.check_access_right_general_manager = True
        else:
            self.check_access_right_general_manager = False    

    @api.one
    @api.depends('first_line_manager_id')
    def check_access_line(self):
        if self.first_line_manager_id.user_id.id == self._uid:
            self.check_access_right_line = True
        else:
            self.check_access_right_line = False

    
    def check_access_admin(self):
       for record in self:
            self.env.cr.execute("""select g.name from (select gid from res_groups_users_rel where uid=%s)gu
            join (select id,name,category_id from res_groups)g on g.id=gu.gid join 
            (select id,name from ir_module_category)m on m.id = g.category_id
            where g.name ~* 'HR' or g.name ~* 'Admin' and m.name ~* 'Evaluation' """, (self.env.uid,))
            admin = self.env.cr.fetchone()
            if admin:
                record.check_access_right_admin = True

        
    @api.one
    @api.depends('period_id')
    def _get_period_status(self):
        self.evaluation_status = self.period_id.evaluation_status

    
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(Evaluation, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        user = self.env['hr.employee'].search([('user_id', '=', self.env.uid)])
        fields = res.get('fields')
        emp_ids = ''
        filtered_users = []
        filter_period = []
        if fields.get('employee_id'):
            self.env.cr.execute("""select id from evaluation_period where is_active=True and evaluation_status ='normal'""")
            active_period = self.env.cr.fetchone()
            if active_period:
                self.env.cr.execute("""select employee_id from evaluation_evaluation where period_id=%s """, (active_period[0],))
                emp_ids = self.env.cr.fetchall()
            

            if self.user_has_groups('ext_evaluation.group_evaluation_admin') or self.user_has_groups('ext_evaluation.group_evaluation_hr') :
                self.env.cr.execute("""select id from evaluation_period where is_active=True""")
                active_period = self.env.cr.fetchall()
                if active_period:
                    period_list = []
                    for p in active_period:
                        period_list.append(p)
                        self.env.cr.execute("""select employee_id from evaluation_evaluation where period_id=%s """, (p,))
                        emp_ids = self.env.cr.fetchall()
                        filtered_users += self.env['hr.employee'].search([('state', '=', 'onboard'),('id', 'not in', tuple(emp_ids))])

            if self.user_has_groups('ext_hr_employee.group_line_manager') :
                # filtered_users += self.env['hr.employee'].search([('line_manager', '=', user.id),('state','=','onboard')])
                filtered_users += self.env['hr.employee'].search([('state', '=', 'onboard'),('id', 'not in', tuple(emp_ids)),('line_manager', '=', user.id)])

            if self.user_has_groups('ext_hr_employee.group_timesheet_approver'):
                # filtered_users += self.env['hr.employee'].search([('timesheet_approver', '=', user.id),('state','=','onboard')])
                filtered_users += self.env['hr.employee'].search([('state', '=', 'onboard'),('id', 'not in', tuple(emp_ids)),('timesheet_approver', '=', user.id)])
            
            if self.user_has_groups('ext_evaluation.group_evaluation_employee'):
                # filtered_users += self.env['hr.employee'].search([('id', '=', user.id),('state','=','onboard')])
                filtered_users += self.env['hr.employee'].search([('state', '=', 'onboard'),('id', 'not in', tuple(emp_ids)),('id', '=', user.id)])

            filtered_users_ids = [x.id for x in filtered_users]
            res['fields']['employee_id']['domain'] = [('id', 'in', filtered_users_ids)]

        if fields.get('period_id'):
            if self.user_has_groups('ext_evaluation.group_evaluation_admin') or self.user_has_groups('ext_evaluation.group_evaluation_hr') :
                filter_period += self.env['evaluation.period'].search([('is_active', 'in', True)])

            else : 
                filter_period += self.env['evaluation.period'].search([('is_active', 'in', True),('evaluation_status','=','normal')])

            filtered_period_ids = [x.id for x in filter_period]
            res['fields']['period_id']['domain'] = [('id', 'in', filtered_period_ids)]

        return res



    @api.model
    def create(self, values):
        emp = self.env['hr.employee'].search([('id', '=', values.get('employee_id'))])
        eval_obj = self.env['evaluation.evaluation'].search([('employee_id', '=', values.get('employee_id')),('period_id','=',values.get('period_id'))])
        if eval_obj:
            raise UserError(_('%s already has evaluation!') % (emp.name))
        values['manager_id'] = emp.timesheet_approver.id
        values['general_manager_id'] = emp.parent_id.id
        values['first_line_manager_id'] = emp.line_manager.id
        
        # store objectives which is not fixed. and then pass it when you want to save the evaluation
        if 'obj_items' in values:
            non_fix_objectives = [x for x in values["obj_items"] if list(x[2].keys())]
            values["obj_items"] =non_fix_objectives
        res = super(Evaluation, self).create(values)
        self.env.cr.execute("""DELETE FROM evaluation_objectives_items WHERE id in
         (select max(id) from evaluation_objectives_items
          where is_fix=True and eval_id is not null
           group by eval_id,category_id,obj_item having count(1)>1)""")
        
        
        #add fix items to evaluation
        evaluation_category = emp.evaluation_category
        fix_templates = self.env['evaluation.fix.template'].search([('category_id', '=', evaluation_category.id), ('state', '=', 'running')])

        if fix_templates:
            fix_template = fix_templates[0]
            
            for fix_item in fix_template.fix_objective_items:
                #create new evaluation objective items / like get template
 
                self.env['evaluation.objectives.items'].create({
                        'category_id':fix_item.category_id.id,
                        'obj_item':fix_item.objective_item_id.id,
                        'eval_id':res.id,
                        'weight':fix_item.weight,
                        'target': fix_item.target,
                        'description': fix_item.description,
                        'is_fix':True,
                        })


                
        return res
      
        
        


    @api.multi
    def write(self, values):
        if 'obj_items' in values and values['obj_items']:
            not_fix_obj_items = []
            for eitem in values['obj_items']:
                values['obj_items']
                if len(eitem) >=2 and eitem[2] != {}:
                    # continue
                    not_fix_obj_items.append(eitem)
            values['obj_items'] = not_fix_obj_items
        
        old_fix_items =[]
        if 'employee_id' in values and values['employee_id']:
            for obj in self.obj_items:
                if obj.is_fix:
                    old_fix_items.append(obj.id)
                    # obj.unlink(force=True)
            # self.eval_items.unlink()
            emp = self.env['hr.employee'].search([('id', '=', values.get('employee_id'))])
            eval_obj = self.env['evaluation.evaluation'].search([('employee_id', '=', values.get('employee_id')),('period_id','=',values.get('period_id'))])
            if eval_obj:
                raise UserError(_('%s already has evaluation!') % (emp.name))
            evaluation_category = emp.evaluation_category

            fix_templates = self.env['evaluation.fix.template'].search([('category_id', '=', evaluation_category.id), ('state', '=', 'running')])
            if fix_templates:
                fix_template = fix_templates[0]
                
                for fix_item in fix_template.fix_objective_items:
                    #create new evaluation objective items / like get template
                    self.env['evaluation.objectives.items'].create({
                        'category_id':fix_item.category_id.id,
                        'obj_item':fix_item.objective_item_id.id,
                        'eval_id':self.id,
                        'weight':fix_item.weight,
                        'target': fix_item.target,
                        'description': fix_item.description,
                        'is_fix':True,
                    })
        


        res = super(Evaluation, self).write(values)

        if self.general_manager_id==False:
            self.general_manager_id = self.employee_id.parent_id



        
        if old_fix_items:
            old_fix_items += [-1,-2]
            self.env.cr.execute("""
                DELETE FROM evaluation_objectives_items WHERE id in {}
            """.format(tuple(old_fix_items)))
        self.env.cr.execute("""DELETE FROM evaluation_objectives_items WHERE id in
         (select max(id) from evaluation_objectives_items
          where is_fix=True and eval_id is not null
           group by eval_id,category_id,obj_item having count(1)>1)""")

    

        
        if self.mng_score != 0 and self.general_mng_score != 0 and self.lm_score == 0:
            if self.mng_eval_status in ('unchanged','edited'):
                if self.general_mng_score != self.mng_score:
                    self.env.cr.execute("""UPDATE evaluation_evaluation SET mng_eval_status=%s WHERE id=%s""",
                                                ('edited', self.id,))
                else:
                    self.env.cr.execute("""UPDATE evaluation_evaluation SET mng_eval_status=%s WHERE id=%s""",
                                        ('unchanged', self.id,))
 



        if self.mng_score != 0 and self.general_mng_score != 0 and self.lm_score != 0:
            if self.mng_eval_status in ('lm_unchanged','lm_edited'):
                if self.general_mng_score != self.lm_score:
                    self.env.cr.execute("""UPDATE evaluation_evaluation SET mng_eval_status=%s WHERE id=%s""",
                                                ('lm_edited', self.id,))
                else:
                    self.env.cr.execute("""UPDATE evaluation_evaluation SET mng_eval_status=%s WHERE id=%s""",
                                        ('lm_unchanged', self.id,))
            

        return res

    





    @api.depends('employee_id')
    def _get_name(self):
        for rec in self:
            rec.name = rec.employee_id.name
            rec.first_line_manager_id =  rec.employee_id.line_manager
            rec.second_line_manager_id = rec.employee_id.line_manager.line_manager
            rec.manager_id = rec.employee_id.timesheet_approver
            # rec.general_manager_id = rec.employee_id.parent_id
            rec.write({'general_manager_id' : rec.employee_id.parent_id.id or False})

    # @api.one
    # def read(self, fields=None, load='_classic_read'):
    #     self.ensure_one()
        
    #     self.write({'general_manager_id':self.employee_id.parent_id.id})
    #     return super(Evaluation, self).read(fields=fields, load=load)
    # @api.one
    # @api.onchange('employee_id')
    # def onchange_general_manager_id(self):
    #     self.general_manager_id = self.employee_id.parent_id    


    # @api.one    
    # @api.depends('employee_id')
    # def _get_gm_name(self):
    #     self.general_manager_id = self.employee_id.parent_id





    @api.multi
    @api.depends('eval_items')
    def _ind_total_score(self):
        ind_total_score = 0.0
        sum_weight = 0.0
        total_score = 0.0
        if self.eval_items:
            for items in self.eval_items:
                if not items.is_fix:
                    target = items.ind_target
                    weight = items.weight
                    score = (target * weight)
                    sum_weight += weight
                    ind_total_score += score
            if sum_weight:
                total_score = ind_total_score/sum_weight
            

        self.ind_total_score =  total_score
        
    
    @api.one
    @api.depends('eval_items_manager')
    def _manager_score(self):
        mng_total_score = 0.0
        general_mng_total_score = 0.0
        lm_total_score = 0.0
        sum_weight = 0.0
        mng_total = 0.0
        general_mng_total = 0.0
        lm_total = 0.0
        # print('****************>>>>>>>>>>', self.id)
        if self.eval_items_manager:
            for items in self.eval_items_manager:
                if not items.is_fix:
                    mng_target = items.manager_score
                    general_mng_target = items.general_manager_score
                    lm_target = items.lm_score
                    weight = items.weight
                    mng_scores = (mng_target * weight)
                    general_mng_scores = (general_mng_target * weight)
                    lm_scores = (lm_target * weight)
                    sum_weight += weight
                    mng_total_score += mng_scores
                    general_mng_total_score += general_mng_scores
                    lm_total_score += lm_scores
            if sum_weight:
                mng_total = (mng_total_score/sum_weight)
                general_mng_total = (general_mng_total_score/sum_weight)
                lm_total = (lm_total_score/sum_weight) 
        self.mng_score = mng_total
        self.general_mng_score = general_mng_total
        # print('<<<<<<<<<<<<<<<<<<<<<<<<', general_mng_total)
        self.lm_score = lm_total
        if self.mng_score != 0 and self.general_mng_score == 0 and self.lm_score == 0:
            self.final_score = self.mng_score
        elif  self.mng_score != 0 and self.general_mng_score != 0 and self.lm_score == 0:
            self.final_score = self.general_mng_score
        elif  self.mng_score != 0 and self.general_mng_score != 0 and self.lm_score != 0:
            self.final_score = self.lm_score
    
    @api.one
    def _total_score(self):
        mng_total_score = 0.0
        general_mng_total_score = 0.0
        lm_total_score = 0.0
        sum_weight = 0.0
        mng_total = 0.0
        general_mng_total = 0.0
        lm_total = 0.0
        if self.eval_items_manager:
            for items in self.eval_items_manager:
                mng_target = items.manager_score
                general_mng_target = items.general_manager_score
                lm_target = items.lm_score
                weight = items.weight
                mng_scores = (mng_target * weight)
                general_mng_scores = (general_mng_target * weight)
                lm_scores = (lm_target * weight)
                sum_weight += weight
                mng_total_score += mng_scores
                general_mng_total_score += general_mng_scores
                lm_total_score += lm_scores
            mng_total = (mng_total_score/sum_weight)
            general_mng_total = (general_mng_total_score/sum_weight)
            lm_total = (lm_total_score/sum_weight) 
        self.mng_score = mng_total
        self.general_mng_score = general_mng_total
        self.lm_score = lm_total
        org_score = self.organization_score != '' and self.organization_score/100.0 or 1
        self.total_score = org_score * ((mng_total + general_mng_total + lm_total)/3)

    @api.one
    def reject_manager_score(self):
        # self.env.cr.execute("""UPDATE evaluation_evaluation SET mng_eval_status=%s WHERE id=%s""",
        #                    ('draft', self.id,))
        # self.mng_score = 0 
        # self.general_mng_score = 0
        if  not self.manager_sign:
                raise UserError('The manager needs to sign the score')
        else:        
            for items in self.eval_items_manager:
                items.general_manager_target = 0
            self.mng_eval_status = 'rejected'
            self.manager_sign = False
            self.general_mng_score = 0



        


    @api.one
    def send_to_manager(self):
        if self.obj_items:
            percentage = 0.0
            eval_cat = []
            
            self.env.cr.execute("select distinct category_id from evaluation_objectives_items where eval_id=%s", (self.id,))
            res = self.env.cr.fetchall()
            if not self.employee_id.evaluation_category:
                raise UserError(_('No evaluation category defined in your HR profile!') )

            active_category_items = self.env['evaluation.category.items'].search([('is_active', '=', True),('id', '=', self.employee_id.evaluation_category.id)])
            category_item_name = [x.id for x in active_category_items]
            for category_id in res:
                category_obj = self.env['evaluation.category.items'].search([('id', '=', category_id)])
                percent = category_obj.percentage
                min_count = category_obj.min_count
                self.env.cr.execute("select count(*) from evaluation_objectives_items where category_id=%s and eval_id=%s", (category_id,self.id,))
                count_result = self.env.cr.fetchone()[0]
                if count_result < min_count:
                    raise UserError(_('You must choose minimum %s items for %s') % (min_count,category_obj.name))
                self.env.cr.execute("select sum(weight) from evaluation_objectives_items where category_id=%s and eval_id=%s", (category_id,self.id,))
                result = self.env.cr.fetchone()[0]
                eval_cat.append(category_obj.id)
                if result < percent or result > percent:
                    raise UserError(_('Sum of %s weight must be %s') % (category_obj.name,percent))
            # filtered_category = list(set(category_item_name).intersection(eval_cat))
            # not_category_item = list(filter(lambda x:x not in eval_cat,category_item_name ))
            # if not_category_item !=[]:
            #     for items in not_category_item:
            #         search_cat = self.env['evaluation.category.items'].search([('id', '=', items)])
            #         raise UserError(_(' %s not set') % (search_cat.name))
            self.env.cr.execute("select sum(weight) from evaluation_objectives_items where eval_id=%s", (self.id,))
            final_result = self.env.cr.fetchone()[0]
            if final_result < 100 or final_result >100:
                raise UserError(_('Objective Items weight must be 100 !') )
            for obj in self.obj_items:
                if obj.target == 0.0:
                    raise UserError(_('Target can not be 0 !') )

            self.state = 'waiting_for_mng'
        else:
            raise UserError(_('Objective Items must be set !') )

    @api.one
    def send_to_general_manager(self):
        self.state = 'waiting_for_general_mng'

    @api.one
    def send_to_lm(self):
        self.state = 'waiting_for_lm'



    @api.one
    def hr_send_to_lm(self):
        self.state = 'waiting_for_lm'

    @api.multi
    def send_emp_eval(self):

        if self.obj_items:
            evaluation_rec = self.env['evaluation.items']
            #delete objective items row if exsist
            if self.eval_items:
                self.eval_items.unlink()
            for obj in self.obj_items:
                evaluation_rec.create({'category_id': obj.category_id.id,
                                        'obj_item': obj.obj_item.id,
                                        'eval_id':self.id,
                                        'weight':obj.weight,
                                        'target':obj.target,
                                        'description':obj.description})
                self.state = 'emp_eval'
        else :
            raise UserError(_('There is not any objective item!'))
        

    @api.one
    def manager_send_to_draft(self):
        self.state = 'draft'

    @api.one
    def general_manager_send_to_draft(self):
        self.state = 'draft'    

    @api.one
    def lm_send_to_draft(self):
        self.state = 'draft'
    @api.one
    def emp_send_to_draft(self):
        self.state = 'draft'

    @api.one
    def send_manager_eval(self):
        evaluation_rec = self.env['evaluation.items.manager']
        if self.period_id.evaluation_status=='self_assessment':
            for eval in self.eval_items:
                if not (eval.ind_target and eval.ind_target_result) and not eval.is_fix:
                    raise UserError(_('Ind. Target Result must be filled!'))
                else:
                    if eval.ind_target < 1 and not eval.is_fix:
                        raise UserError(_('Ind. Score Should be between 1-125!'))
                    evaluation_rec.create({'category_id': eval.category_id.id,
                                        'obj_item': eval.obj_item.id,
                                        'eval_id':self.id,
                                        'weight':eval.weight,
                                        'target':eval.target,
                                        'ind_target_result':eval.ind_target_result,
                                        'ind_target':eval.ind_target,
                                        'eval_item':eval.id})
                    self.manager_sign = False
                    self.lm_sign = False
                    self.state = 'mng_eval'
        # else:
        #     raise UserError(_('In Self Assesment period you can use this.'))

    @api.one
    def force_send_manager_eval(self):
        evaluation_rec = self.env['evaluation.items.manager']
        if self.period_id.evaluation_status=='manager_assessment':
            for eval in self.eval_items:
                
                evaluation_rec.create({'category_id': eval.category_id.id,
                                    'obj_item': eval.obj_item.id,
                                    'eval_id':self.id,
                                    'weight':eval.weight,
                                    'target':eval.target,
                                    'ind_target_result':eval.ind_target_result,
                                    'ind_target':eval.ind_target,
                                    'eval_item':eval.id})
                self.manager_sign = False
                self.lm_sign = False
                self.state = 'mng_eval'

    @api.one
    def lm_evaluated(self):
        
        for eval in self.eval_items_manager:
            evaluation_rec = self.env['evaluation.items'].search([('id', '=', eval.eval_item.id)])
            if not eval.is_fix and not (eval.lm_target and eval.lm_score):
                raise UserError(_('LM Target Result must be filled!'))
            else :
                if not eval.is_fix and  eval.lm_score < 1:
                    raise UserError(_('LM Score Should be between 1-125!'))
                if self.general_manager_sign:
                    self.lm_sign = True
                    evaluation_rec.update({
                                        'lm_target':eval.lm_target,
                                        'lm_score':eval.lm_score,
                                        })
                    self.state = 'emp_review'
                if not self.general_manager_sign :
                    self.general_manager_sign = True
                    self.lm_sign = True
                    evaluation_rec.update({
                                        'lm_target':eval.lm_target,
                                        'lm_score':eval.lm_score,
                                        })
                    self.state = 'emp_review'                    
    @api.one
    def general_manager_evaluated(self):
        for eval in self.eval_items_manager:
            evaluation_rec = self.env['evaluation.items'].search([('id', '=', eval.eval_item.id)])
            if not eval.is_fix and not (eval.general_manager_target and eval.general_manager_score):
                raise UserError(_('General Manager Target Result must be filled!'))
            else :
                if not eval.is_fix and  eval.general_manager_score < 1:
                    raise UserError(_('General Manager Score Should be between 1-125!'))
                if self.manager_sign:
                    self.general_manager_sign = True
                    evaluation_rec.update({
                                        'general_manager_target':eval.general_manager_target,
                                        'general_manager_score':eval.general_manager_score,
                                        })
                    eval.update({
                                'lm_target':eval.general_manager_target,
                                'lm_score' :eval.general_manager_score,
                                })                    
                    self.general_manager_sign = True
                    self.mng_eval_status = 'lm_unchanged'                     
                    # self.state = 'emp_review'

                # it does not make senese to me!    
                elif not self.manager_sign :
                    self.general_manager_sign = True
                    evaluation_rec.update({
                                        'general_manager_target':eval.general_manager_target,
                                        'general_manager_score':eval.general_manager_score,
                                        })
                    eval.update({
                                'lm_target':eval.general_manager_target,
                                'lm_score' :eval.general_manager_score,
                                })                      
                    self.general_manager_sign = True
                    self.mng_eval_status = 'lm_unchanged' 
                self.lm_score = self.general_mng_score                           
 


            

                                        

    @api.one
    def manager_evaluated(self):
        for eval in self.eval_items_manager:
            evaluation_rec = self.env['evaluation.items'].search([('id', '=', eval.eval_item.id)])
            # evaluation_rec_mng = self.env['evaluation.items.manager'].search([('id', '=', eval.eval_item.id)])

            if not eval.is_fix and not (eval.manager_target and eval.manager_score):
                raise UserError(_('Manager Target Result must be filled!'))
            else :
                if not eval.is_fix and eval.manager_score < 1:
                    raise UserError(_('Manager Score Should be between 1-125!'))
                else:
                    evaluation_rec.update({
                                        'manager_target':eval.manager_target,
                                        'manager_score':eval.manager_score,
                                        })
                    eval.update({
                                'general_manager_target':eval.manager_target,
                                'general_manager_score' : eval.manager_score,
                                })

                    # self.env.cr.execute("""UPDATE evaluation_items_manager SET general_manager_target=%s , general_manager_score=%s WHERE id=%s""",
                    #                     (eval.manager_target,eval.manager_score, eval.id,))            
                    self.manager_sign = True
                    self.mng_eval_status = 'unchanged'
                    self.general_mng_score = self.mng_score






                    # self.state = 'emp_review'
                # else :
                #     self.general_manager_sign = True
                #     evaluation_rec.update({
                #                         'manager_target':eval.manager_target,
                #                         'manager_score':eval.manager_score,
                #                         })


    @api.one
    def send_to_claim(self):
        if self.claim == False:
            self.manager_sign = False
            self.general_manager_sign = False
            self.lm_sign = False
            self.claim = True
            self.state = 'claim'

    @api.one
    def send_to_done(self):
        score_obj = self.env['evaluation.score']
        if self.score_id:
            old_rates = self.env['evaluation.score'].search([('id', '=', self.score_id.id)])
            old_rates.update({'value':self.final_score}) 
        else:
            sid=score_obj.create({'employee_id': self.employee_id.id,
                                'period_id': self.period_id.id,
                                'value':self.final_score,
                                'state':'validated',
                                'score_type_id':2})
            self.score_id = sid

        self.state = 'done'

    @api.one
    def reject_to_emp(self):
        if self.eval_items_manager:
            self.eval_items_manager.unlink()
        self.state = 'emp_eval'

    @api.one
    def reject_to_manager(self):
        self.lm_sign = False
        self.general_manager_sign = False
        self.manager_sign = False
        self.state = 'mng_eval'

    @api.multi
    def unlink(self):
        for item in self:
            if item.state !='draft':
                raise UserError(_('Cannot delete evaluation in %s state!')%(item.state))
            else:
                if item.obj_items:
                    item.obj_items.unlink()
                return super(Evaluation, self).unlink()
    

    @api.multi
    def get_template_value(self):
        if self.tmp_id:
            obj_name = self.tmp_id.objective_items
            objective_rec = self.env['evaluation.objectives.items']
            #delete objective items row if exsist
            if self.obj_items:
                self.obj_items.search([('eval_id', '=', self.id),('is_fix', '=', False)]).unlink()

            for obj in obj_name:
                objective_rec.create({'category_id': obj.category_id.id,'obj_item': obj.obj_item.id,
                                            'eval_id':self.id,'weight':obj.weight,'target':obj.target,'description':obj.description})
        else :
            raise UserError(_('You must select template!'))
        return True



class EvaluationObjectivesItems(models.Model):
    _name = "evaluation.objectives.items"
    _description = "Evaluation Objectives Items"
    _order = 'category_id'

    category_id = fields.Many2one('evaluation.category.items', string="Category Name",domain="[('is_active','=',True)]", required=True)
    obj_item = fields.Many2one('evaluation.objectives', string="Objective Name",  required=True,domain=[('state', '=','running'),('type_of_category_item','=','category_id'), ('is_fix', '=', False)])
    eval_id = fields.Many2one('evaluation.evaluation', string="Evaluation",invisible=True)
    weight = fields.Float(string="Weight")
    target = fields.Float(string="Target")
    description = fields.Text(string="Description")
    is_fix = fields.Boolean(string="Is Fix", default=False, readonly=True)
    generator_id = fields.Many2one('evaluation.objective_generator', string="Generator")
    eval_state = fields.Selection(related='eval_id.state', string="Evaluation State")
    # domain_category_items_id = fields.Many2many('evaluation.category.items', 'evaluation_category_items_rel', 'eval_id', 'category_id', string="Categories",compute='_compute_category_id')


    @api.model
    def create(self, values):
        obj_items = self.env['evaluation.objectives.items'].search([('eval_id','=',values.get('eval_id')),('is_fix','=', True)])
        objs = [x.obj_item.id for x in obj_items]

        #check if new objective exist in already created objectives list of evaluation
        if values.get('obj_item') not in objs:
            return super(EvaluationObjectivesItems,self).create(values)
        else:
            res = self.env['evaluation.objectives.items'].browse(-1)
            return res




    @api.multi
    @api.onchange('category_id','eval_id')
    def onchange_category_id(self):
        filtered_template = []
        general_cond = []
        if self.eval_id.employee_id:
            if not self.eval_id.employee_id.evaluation_category:
                raise UserError(_('No evaluation category defined in your HR profile!'))
            self.obj_items = ''
            self.env.cr.execute(
                """select id from evaluation_category where is_active=True and id =%s""",
                (self.eval_id.employee_id.evaluation_category.id,))
            active_category_items = self.env.cr.fetchall()
            active_category = self.env['evaluation.category.items'].search(
                [('is_active', '=', True), ('category_id', '=', active_category_items[0][0])])
            # active_category_items = self.env['evaluation.category'].search([('is_active', '=', True),('id', '=', self.employee_id.evaluation_category.id)])
            # for category_id in active_category:
            #     general_cond += self.env['evaluation.objectives.items'].search(
            #         [('category_id', '=', category_id.id)])

            general_cond = [x.id for x in active_category]
            filtered_template = list(general_cond)

        return {'domain': {'category_id': [('id', 'in', filtered_template)]}}
    
    
    @api.multi
    def unlink(self, force=False):
        for obj in self:
            if obj.is_fix and not force:
                raise UserError(_('You Can not delete the Objective which is Fix'))
        return super(EvaluationObjectivesItems, self).unlink()

    @api.multi
    @api.onchange('category_id','eval_id')
    def onchange_category_items(self):

        filtered_objective = []
        general_cond = []
        spcific_cond = []
        if self.category_id:
            self.obj_item = ''
            general_cond += self.env['evaluation.objectives'].search([('type_of_category_item', '=', self.category_id.id),('state', '=','running')])
            spcific_cond += self.env['evaluation.objectives'].search([('lm_name', '=', self.eval_id.first_line_manager_id.id)])
            spcific_cond += self.env['evaluation.objectives'].search([('obj_type','=','public')])
            
            general_cond = [x.id for x in general_cond]
            spcific_cond = [x.id for x in spcific_cond]
            filtered_objective = list(set(general_cond).intersection(spcific_cond))
            
        return {'domain':{'obj_item':[('id', 'in', filtered_objective), ('is_fix', '=', False)]}}


class EvaluationItems(models.Model):
    _name = "evaluation.items"
    _description = "Evaluation Items"


    category_id = fields.Many2one('evaluation.category.items', string="Category Name",readonly=True)
    obj_item = fields.Many2one('evaluation.objectives', string="Objective Name",readonly=True)
    eval_id = fields.Many2one('evaluation.evaluation', string="Evaluation",readonly=True)
    period_id = fields.Many2one('evaluation.period', string="Period", readonly=True, related = "eval_id.period_id", store=True)
    weight = fields.Float(string="Weight",readonly=True)
    target = fields.Float(string="Target",readonly=True)
    ind_target_result = fields.Float(string="Ind. Target Result")
    ind_target = fields.Float(string="Ind. Score",compute='_compute_ind_score',store=True)
    manager_target = fields.Float(string="Manager Target Result" ,readonly=True)
    manager_score = fields.Float(string="Manager Score" ,readonly=True)
    general_manager_target = fields.Float(string="General Manager Target Result" ,readonly=True)
    general_manager_score = fields.Float(string="General Manager Score" ,readonly=True)
    lm_target = fields.Float(string="LM Target Result" ,readonly=True)
    lm_score = fields.Float(string="LM Score" ,readonly=True)
    is_fix = fields.Boolean(string="is Fix?", related="obj_item.is_fix")

    @api.depends('ind_target_result')
    def _compute_ind_score(self):
        """Compute the IND.score base on Ind.Target result, between 0 and 125"""
        for t in self:
            calc = (t.ind_target_result * 100)/t.target
            if calc <= 125:
                t.ind_target =  calc
            else:
                raise UserError(_('Score Should be between 1-125!'))


class EvaluationItems_manager(models.Model):
    _name = "evaluation.items.manager"
    _description = "Evaluation Items Manager"


    category_id = fields.Many2one('evaluation.category.items', string="Category Name",readonly=True)
    eval_item = fields.Many2one('evaluation.items', string=" Items",readonly=True)
    obj_item = fields.Many2one('evaluation.objectives', string="Objective Name",readonly=True)
    eval_id = fields.Many2one('evaluation.evaluation', string="Evaluation",readonly=True)
    weight = fields.Float(string="Weight",readonly=True)
    target = fields.Float(string="Target",readonly=True)
    ind_target_result = fields.Float(string="Ind. Target Result",readonly=True)
    ind_target = fields.Float(string="Ind. Score",readonly=True)
    manager_target = fields.Float(string="Manager Target Result")
    manager_score = fields.Float(string="Manager Score",compute='_compute_mng_score',store=True)
    general_manager_target = fields.Float(string="General Manager Target Result", default=0)
    general_manager_score = fields.Float(string="General Manager Score",compute='_compute_general_mng_score')
    lm_target = fields.Float(string="LM Target Result")
    lm_score = fields.Float(string="LM Score",compute='_compute_lm_score',store=True)
    is_fix = fields.Boolean(string="Is Fix", related='eval_item.is_fix')

    # @api.multi
    # @api.onchange('general_manager_target')
    # def _onchange_gm_target(self):
    #     # Compare general manger score with manager score
    #     lb = 0.95*self.manager_target
    #     ub = 1.05*self.manager_target
    #     if self.general_manager_target < lb or self.general_manager_target > ub:
    #         raise UserError(_('Target Should be between [%s - %s] !') % (lb, ub))



    @api.depends('manager_target')
    def _compute_mng_score(self):
        """Compute the Manager score base on Manager Target result, between 0 and 125"""
        for t in self:
            calc = (t.manager_target * 100)/t.target
            if calc <= 125:
                t.manager_score =  calc
            else:
                raise UserError(_('Score Should be between 1-125!'))


    @api.depends('general_manager_target')
    def _compute_general_mng_score(self):
        """Compute the General Manager score base on General Manager Target result, between 0 and 125"""
        # c = 0
        for t in self:
            # c += 1
            # print('**************',c, len(self))
            # print('calc, t.id--------->',t.general_manager_target ,t.target, t.id)
            calc = (t.general_manager_target * 100)/t.target
           
            if calc <= 125:
                # print('1')
                t.general_manager_score =  calc
            else:
                # print('2')
                raise UserError(_('Score Should be between 1-125!'))
        #     print('end')  
        # return       


    @api.depends('lm_target')
    def _compute_lm_score(self):
        """Compute the LM score base on LM Target result, between 0 and 125"""
        for t in self:
            calc = (t.lm_target * 100)/t.target
            if calc <= 125:
                t.lm_score =  calc
            else:
                raise UserError(_('Score Should be between 1-125!'))


class EvaluationChangeStatusWizard(models.TransientModel):
    _inherit = ['mail.thread']
    _name = "evaluation.change_status_wizard"

    @api.one
    def approve_all(self):
        res_user = self.env['res.users'].search([('id', '=', self._uid)])
        context = self._context
        # active_ids = context.get('active_ids')
        eval_ids = self.env.context.get('active_ids', [])
        all_eval_ids = self.env['evaluation.evaluation'].browse(eval_ids)
        for eval_id in all_eval_ids:
            if not eval_id:
                continue
            if eval_id.state in ('claim', 'emp_review'):
                if eval_id.period_id.evaluation_status != 'manager_assessment':
                    raise UserError(_('Evaluation Should be in Manager Assessment State!'))
                score_obj = self.env['evaluation.score']
                if eval_id.score_id:
                    old_rates = self.env['evaluation.score'].search([('id', '=', eval_id.score_id.id)])
                    old_rates.update({'value': eval_id.final_score})
                else:
                    sid = score_obj.create({'employee_id': eval_id.employee_id.id,
                                            'period_id': eval_id.period_id.id,
                                            'value': eval_id.final_score,
                                            'state': 'validated',
                                            'score_type_id': 2})
                    # eval_id.score_id = sid
                    self.env.cr.execute("""UPDATE evaluation_evaluation SET score_id=%s WHERE id=%s""",
                                        (sid.id, eval_id.id,))

                self.env.cr.execute("""UPDATE evaluation_evaluation SET state='done' WHERE id=%s""",
                                    (eval_id.id,))
                message = "Evaluation Updated by {}".format(res_user.login)
                eval_id.message_post(message)
            if eval_id.state == "emp_eval":
                evaluation_rec = self.env['evaluation.items.manager']
                if eval_id.period_id.evaluation_status not in ('self_assessment', 'manager_assessment'):
                    raise UserError(_('Evaluation Should be in Self/Manager Assessment State!'))
                for eval in eval_id.eval_items:
                    if not (eval.ind_target and eval.ind_target_result) and not eval.is_fix:
                        eval.ind_target = 0
                        eval.ind_target_result =0
                    evaluation_rec.create({'category_id': eval.category_id.id,
                                           'obj_item': eval.obj_item.id,
                                           'eval_id': eval_id.id,
                                           'weight': eval.weight,
                                           'target': eval.target,
                                           'ind_target_result': eval.ind_target_result,
                                           'ind_target': eval.ind_target,
                                           'eval_item': eval.id})

                self.env.cr.execute(
                    """UPDATE evaluation_evaluation SET state='mng_eval',manager_sign=False,lm_sign=False WHERE id=%s""",
                    (eval_id.id,))
                message = "Evaluation Updated by {}".format(res_user.login)
                eval_id.message_post(message)

