# -*- coding: utf-8 -*-


from cmath import nan
import string
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import time, math



class ApproverPanel(models.Model):
    _name = "approver.panel"
    _description = "Timesheet Approver Panel"

    name = fields.Char(string='Timesheet Approver Panel', compute='_get_name')
    timesheet_approver_id = fields.Many2one('hr.employee', string='Timesheet Approver', required=True, domain=[('state','=','onboard')])
    period_id = fields.Many2one('evaluation.period', string="Period", required=True, )
    # approval_status = fields.Boolean(string="Approval Status", related='' readonly=True, )
    evaluation_ids = fields.One2many('evaluation.evaluation','approver_panel_id', string="Evaluations",domain=[('state', '!=', 'draft')])
    check_access_right = fields.Boolean(compute="_check_access",string='Access Right',readonly=True,)
    state = fields.Selection([
        ('draft', 'Draft'),         
        ('open_for_approver', 'Timesheet Approver Evaluation'),
        ('done', 'Done')],
        string='Status', default='draft', readonly=True, compute='_get_state')
    
    @api.one
    @api.depends('period_id','evaluation_ids')
    def _get_state(self):
        if self.evaluation_ids:
            manager_signed = True
            for eval in self.evaluation_ids:
                if eval.manager_sign == False:
                    manager_signed = False
                    break
            if self.period_id.evaluation_status == 'manager_assessment' and manager_signed: 
                self.state = 'done'       
            elif self.period_id.evaluation_status == 'manager_assessment':
                self.state = 'open_for_approver'
            else:
                self.state = 'draft'
        else:
            self.state = 'draft'        


            
    @api.model
    def create(self, values):
        evals = self.env['evaluation.evaluation'].search([('period_id','=',values.get('period_id')),('manager_id','=',values.get('timesheet_approver_id')),('state', '!=', 'draft')])

        manager_evaluation = True
        for eval in evals:
            if eval.state not in ['mng_eval',]:
                manager_evaluation = False
                break
        if not manager_evaluation:
           raise UserError('To create Approver Panel, all evaluations need to be in Manager Evaluation status or dissmissed by taking Draft status')  
        return super(ApproverPanel, self).create(values)         


    @api.one
    @api.depends('timesheet_approver_id','period_id')
    def _get_name(self):
        self.name =  str(self.timesheet_approver_id.name) + '-' + str(self.period_id.name)


    @api.one
    @api.depends('timesheet_approver_id', 'period_id')
    def _get_evaluation(self):
        if self.timesheet_approver_id and self.period_id:
            filtered_evaluations = self.env['evaluation.evaluation'].search([('manager_id','=',self.timesheet_approver_id.id),('period_id','=',self.period_id.id), ('state','!=', 'draft')])
            print('filtered_evaluations-------------------------', filtered_evaluations)
            if filtered_evaluations:
                self.evaluation_ids = filtered_evaluations
            # else:
            #     raise UserError(_('No evaluation defined under your supervision in period %s!') %(self.period_id.name))


    @api.one
    @api.depends('timesheet_approver_id')
    def _check_access(self):
        if self.timesheet_approver_id.id == self._uid or self.user_has_groups("ext_evaluation.group_see_all_evaluation"):
            self.check_access_right = True
        else:
            self.check_access_right = False

    # @api.one
    # @api.depends('evaluation_ids')
    # def force_all_send_manager_eval(self):
    #     for eval in self.evaluation_ids:
    #         eval.force_send_manager_eval()



class GeneralManagerPanel(models.Model):
    _name = "general.manager.panel"
    _description = "General Manager Panel"

    name = fields.Char(string='General Manager Panel', compute='_get_name')
    general_manager_id = fields.Many2one('hr.employee', string='General Manager', required=True, domain=[('state','=','onboard')])
    period_id = fields.Many2one('evaluation.period', string="Period", required=True, )
    sample_population = fields.Integer(compute='_calculate_population', string='Sample Population')
    evaluation_ids = fields.One2many('evaluation.evaluation','general_manager_panel_id', string="Evaluations",domain=[('state', '!=', 'draft')])
    check_access_right = fields.Boolean(compute="_check_access",string='Access Right',readonly=True,)
    final_score_distribution_ids = fields.One2many('final.score.distribution','general_manager_panel_id', string='Final Score Distribution')
    state = fields.Selection([
        ('draft', 'Draft'),         
        ('open_for_gm_mng', 'General Manager Evaluation'),
        ('done', 'Done')],
        string='Status', default='draft', readonly=True, compute='_get_state')
    
    approved_deviation = fields.Char(compute='_calculate_first_deviation', string="Maximum Deviation ≃")
    first_deviation = fields.Char(compute='_calculate_first_deviation', )
    first_deviation_count = fields.Char(compute='_calculate_first_deviation', string="Actual Deviation ≃")


    




    @api.one
    @api.depends('general_manager_id', 'period_id')    
    def _calculate_first_deviation(self):
        total_eval_number = self.env['evaluation.evaluation'].search_count([('general_manager_id','=',self.general_manager_id.id),('period_id','=',self.period_id.id),('state', '!=', 'draft')])     
        edited_evaluation = self.env['evaluation.evaluation'].search_count([('second_deviation','!=',0),('general_manager_id','=',self.general_manager_id.id),('period_id','=',self.period_id.id),('state', '!=', 'draft')])

        violation_configuration = self.env['violation.configuration'].search([('period_id','=',self.period_id.id)])
        if total_eval_number != 0:
            # self.first_deviation = f"{round((edited_evaluation/total_eval_number),2) * 100}%"
            self.first_deviation_count = edited_evaluation
            self.first_deviation = round((edited_evaluation/total_eval_number),2)
        else:
            self.first_deviation_count = 0
            self.first_deviation = 0 
        if violation_configuration:    
            self.approved_deviation = f"{math.ceil(total_eval_number * violation_configuration[0].first_deviation_limit)} ({violation_configuration[0].first_deviation_limit * 100}%)"


        # *****************     



    @api.model
    def create(self, values):
        evals = self.env['evaluation.evaluation'].search([('period_id','=',values.get('period_id')),('general_manager_id','=',values.get('general_manager_id')),('state', '!=', 'draft')])
        print('evals*********************', evals)
        manager_evaluation = True
        for eval in evals:
            if eval.state != 'mng_eval':
                manager_evaluation = False
                break
        violation_configuration = self.env['violation.configuration'].search([('period_id','=',values.get('period_id'))])
        if not violation_configuration:
            raise UserError('You need to set derivation configuration for the period!')    
        if not manager_evaluation:
           raise UserError('To create General Manager Panel, all evaluations need to be in Manager Evaluation status!') 
        return super(GeneralManagerPanel, self).create(values) 

    @api.multi
    @api.depends('general_manager_id', 'period_id')
    def _get_evaluation(self):
        if self.general_manager_id and self.period_id:
            print('general_manager_id', self.general_manager_id.id)
            print('general_manager_id', type(self.general_manager_id.id))
            print('period_id', self.period_id.id)
            self.env.cr.execute("""SELECT * from evaluation_evaluation WHERE general_manager_id = %s and period_id= %s and state != 'draft'""",(self.general_manager_id.id, self.period_id.id))
            filtered_evaluations = self.env.cr.fetchall()
            filtered_evaluations = [eval[0] for eval in filtered_evaluations]
            print('filtered_evaluations-------------------------', filtered_evaluations)
            eval_objs = self.env['evaluation.evaluation'].browse(filtered_evaluations)
            # eval_objs = []
            # for eval in filtered_evaluations:
            #     eval_obj = self.env['evaluation.evaluation'].search([('id', '=', eval)])
            #     eval_objs += eval_obj



            # filtered_evaluations = self.env['evaluation.evaluation'].search([('general_manager_id','=',self.general_manager_id.id),('period_id','=',self.period_id.id)])
            print('eval_objs-------------------------', eval_objs)
            if eval_objs:
                # self.evaluation_ids = eval_objs
                 self.sudo().write({'evaluation_ids':[(4,rec.id) for rec in eval_objs]})
                 for rec in eval_objs:
                    print('hiiiiiiiiiiiiiiiii %s' %rec.id)
            # else:
            #     raise UserError(_('No evaluation defined under your supervision in period %s!') %(self.period_id.name))
         
    
    @api.one
    @api.depends('period_id','evaluation_ids')
    def _get_state(self):
        if self.evaluation_ids:
            manager_signed = True
            for eval in self.evaluation_ids:
                if eval.manager_sign == False:
                    manager_signed = False
                    break

            general_manager_signed = True
            for eval in self.evaluation_ids:
                if eval.general_manager_sign == False:
                    general_manager_signed = False
                    break
            if self.period_id.evaluation_status == 'manager_assessment' and manager_signed and general_manager_signed: 
                self.state = 'done'       
            elif self.period_id.evaluation_status == 'manager_assessment' and manager_signed:
                self.state = 'open_for_gm_mng'
            else:
                self.state = 'draft'
        else:
            self.state = 'draft'        


    


    @api.one
    @api.depends('final_score_distribution_ids')
    def all_general_manager_evaluated(self):
        total_eval_number = self.env['evaluation.evaluation'].search_count([('general_manager_id','=',self.general_manager_id.id),('period_id','=',self.period_id.id),('state', '!=', 'draft')])     

        dist_status=True
        for rec in self.final_score_distribution_ids:
            if rec.status != 'in_range':
                dist_status = False
                break
        violation_configuration = self.env['violation.configuration'].search([('period_id','=',self.period_id.id)])
        if violation_configuration:        
            if dist_status == True:
                if int(self.first_deviation_count) <= int(math.ceil(total_eval_number * violation_configuration[0].first_deviation_limit)):
                    for eval in self.evaluation_ids:
                        if float(eval.second_deviation) <= float(violation_configuration[0].second_deviation_limit):
                            eval.general_manager_evaluated()
                        else:
                            raise UserError(('The submitted score for %s is violating ±%s deviation rule!') % (eval.employee_id.name,violation_configuration[0].second_deviation_limit * 100))
                else:
                    raise UserError(('The number of edited evaluations is violating +%s deviation rule!') % (violation_configuration[0].first_deviation_limit * 100,))
            else:
                raise UserError('To approve all evaluations, evaluation sample need to have Normal Distribution')

        






    @api.one
    @api.depends('general_manager_id','period_id')
    def _calculate_population(self):
        self.env.cr.execute("""SELECT COUNT(*) FROM evaluation_evaluation WHERE period_id = %s and
                                                     general_manager_id = %s and state != 'draft'""", (self.period_id.id, self.general_manager_id.id,))
        self.sample_population = self.env.cr.fetchone()[0]                                             

    def calculate_distribution(self):
        self.env.cr.execute("""SELECT COUNT(*) FROM evaluation_evaluation WHERE period_id = %s
                                              and general_manager_id = %s and mng_eval_status IN ('unchanged','edited') and state != 'draft'""",
                                              (self.period_id.id, self.general_manager_id.id,))
        evaluated_evals = self.env.cr.fetchone()[0]                                      
        print("evaluated_evals------------------->", evaluated_evals) 
        print("sample_population------------------->", self.sample_population)                                     
        if evaluated_evals == self.sample_population:                   
            self.env.cr.execute("""DELETE FROM final_score_distribution WHERE general_manager_panel_id = %s""", (self.id,))
            if self.sample_population >= 20:
                self._distribution_gt_twenty()
            else:
                self._distribution_lt_twenty()  
               
        else:
           raise UserError('All evaluations need to be in edited or unchanged status!')


    def _distribution_gt_twenty(self):
        filtered_normal_distribution = self.env['normal.distribution'].search([('period_id','=',self.period_id.id),('distribution_type','=','gt_twenty')])
        filtered_normal_distribution_items = filtered_normal_distribution.distribution_items_ids
        print('filtered_normal_distribution_items----->',filtered_normal_distribution_items)                                                                 
        if  filtered_normal_distribution_items:                                                                
            for rec in filtered_normal_distribution_items:
                n1 = 0.1
                ru = (math.ceil(self.sample_population * rec.percentage) - (self.sample_population * rec.percentage))/(self.sample_population * rec.percentage)
                rd = abs((math.floor(self.sample_population * rec.percentage) - (self.sample_population * rec.percentage))/(self.sample_population * rec.percentage))
                if ru == 0 and rd == 0:
                    negative_deviation = positive_deviation = 0.1
                else:
                    negative_deviation = rd
                    positive_deviation = ru 
                min_count = round(self.sample_population*rec.percentage*(1-negative_deviation))
                max_count = round(self.sample_population*rec.percentage*(1+positive_deviation))   

                self.env.cr.execute("""SELECT COUNT(*) FROM evaluation_evaluation WHERE period_id = %s
                                                    and general_manager_id = %s and final_score >= %s and final_score < %s and state != 'draft'""",
                                                    (self.period_id.id, self.general_manager_id.id,rec.lower_limit, rec.upper_limit,))
                actual_count = self.env.cr.fetchone()[0]

                if actual_count >= min_count and actual_count <= max_count:
                    status = 'in_range'
                else:
                    status = 'out_of_range'  

                self.env['final.score.distribution'].create({
                    'general_manager_panel_id': self.id,
                    'percentage': rec.percentage,
                    'min_count' : min_count,
                    'max_count' : max_count,
                    'lower_limit': rec.lower_limit,
                    'upper_limit': rec.upper_limit,
                    'actual_count': actual_count,
                    'status':status,

                })
        else:
           raise UserError('There are NOT any defined distribution for population greater than 20 for this period!')            

    def _distribution_lt_twenty(self):
        # filtered_normal_distribution_items = self.env.cr.execute("""SELECT * FROM normal_distribution WHERE period_id = %s and
        #                                                         distribution_type = %s """, (self.period_id.id,'lt_twenty'))
        # filtered_normal_distribution_items = self.env.cr.fetchall()
        filtered_normal_distribution = self.env['normal.distribution'].search([('period_id','=',self.period_id.id),('distribution_type','=','lt_twenty')])
        filtered_normal_distribution_items = filtered_normal_distribution.distribution_items_ids
        print('filtered_normal_distribution_items----->',filtered_normal_distribution_items) 


        if filtered_normal_distribution_items:
            # filtered_normal_distribution_items.sort(key=lambda x:x.lower_limit)
            actual_count_dict = {}
            for rec in filtered_normal_distribution_items:
                self.env.cr.execute("""SELECT COUNT(*) FROM evaluation_evaluation WHERE period_id = %s
                                                    and general_manager_id = %s and final_score >= %s and final_score < %s and state != 'draft'""",
                                                    (self.period_id.id, self.general_manager_id.id,rec.lower_limit, rec.upper_limit,))
                actual_count = self.env.cr.fetchone()[0]
                actual_count_dict[rec.lower_limit] = actual_count
                print('actual_count_dict------>',actual_count_dict)
                print('actual_number--------------->', actual_count)

                if rec.lower_limit == 110:
                    min_count = 0
                    max_count = 1 
                elif rec.lower_limit == 100:
                    min_count = 0
                    max_count = [round(0.1*self.sample_population) - actual_count_dict[110] if round(0.1*self.sample_population) > 1 else 1 - actual_count_dict[110]]
                    max_count = max_count[0]
                    # max_count = max(0,round(0.1*self.sample_population) - actual_count_dict[110])
                elif rec.lower_limit == 90:
                    min_count = round(0.4*self.sample_population)
                    max_count = round(0.4*self.sample_population)         
                elif rec.lower_limit == 0:
                    min_count = round(0.5*self.sample_population)
                    max_count = round(0.6*self.sample_population)

 


                if actual_count >= min_count and actual_count <= max_count:
                    status = 'in_range'
                else:
                    status = 'out_of_range'          

                self.env['final.score.distribution'].create({
                    'general_manager_panel_id': self.id,
                    'percentage': round((max_count/self.sample_population)*100),
                    'min_count' : min_count,
                    'max_count' : max_count,
                    'lower_limit': rec.lower_limit,
                    'upper_limit': rec.upper_limit,
                    'actual_count': actual_count,
                    'status': status,

                })
        else:
            raise UserError('There are NOT any defined distribution for population less than 20 for this period!')        
                                                                                       
        


    @api.one
    @api.depends('general_manager_id','period_id')
    def _get_name(self):
        self.name =  str(self.general_manager_id.name) + '-' + str(self.period_id.name)


    @api.one
    @api.depends('general_manager_id')
    def _check_access(self):
        if self.general_manager_id.id == self._uid or self.user_has_groups("ext_evaluation.group_see_all_evaluation"):
            self.check_access_right = True
        else:
            self.check_access_right = False


class FinalScoreDistribution(models.Model):
    _name = 'final.score.distribution'
    _description = 'Final Score Distribution'

    general_manager_panel_id = fields.Many2one('general.manager.panel', string="General Manager Plan",)
    line_manager_panel_id = fields.Many2one('line.manager.panel', string="Line Manager Plan",)
    distribution_item_id = fields.Many2one('normal.distribution.items', string='Range and Corrosponding Weight', store=True,)
    period_id = fields.Many2one(related = 'general_manager_panel_id.period_id', string='Period',)
    lower_limit = fields.Integer(string='Item Lower Limit')
    upper_limit = fields.Integer(string='Item Upper Limit')
    percentage = fields.Float(string='Percentage')
    min_count = fields.Integer(string='Minimum Count')
    max_count = fields.Integer(string='Maximum Count')
    actual_count = fields.Integer(string='Actual Count')
    status = fields.Selection([
        ('in_range', 'In Range'),
        ('out_of_range','Out of Range')
    ], string='Staus')

    # @api.multi
    # @api.onchange('evaluation_ids')
    # def onchange_evaluation(self):
    #     print('I am changing !!!!!!!!!!!!!!!!!!!!!!!!!!!!!')        



class NormalDistribution(models.Model):
    _name = 'normal.distribution'
    _description = 'Normal Distribution'

    name = fields.Many2one(string="Normal Distribution",compute='_get_name')
    period_id = fields.Many2one('evaluation.period', string="Period", required=True, )
    is_active = fields.Boolean(string="Active")
    distribution_type = fields.Selection([
        ('gt_twenty','Greater than 20'),
        ('lt_twenty', 'Less than 20'),
    ])
    distribution_items_ids = fields.One2many('normal.distribution.items','normal_distribution_id',string='Range and Corrosponding Weight', store=True, )


    # @api.one
    # @api.depends('sample_population')
    # def _calculate_interval(self):
    #     distribution = [0.025, 0.075, 0.4, 0.4, 0.075,0.025]
    #     for percentage in  distribution:
    #         n1 = 0.1
    #         ru = (math.ceil(self.sample_population*percentage) - (self.sample_population*percentage))/(self.sample_population*percentage)
    #         rd = abs((math.floor(self.sample_population*percentage) - (self.sample_population*percentage))/(self.sample_population*percentage))
    #         if ru == 0 and rd == 0:
    #             negative_deviation = positive_deviation = 0.1
    #         else:
    #             negative_deviation = rd
    #             positive_deviation = ru   
    #             self.env['normal.distribution.items'].create({
    #                 'percentage': percentage,
    #                 'lower_limit' : round(self.sample_population*percentage*(1-negative_deviation)),
    #                 'upper_limit' : round(self.sample_population*percentage*(1+positive_deviation)),
    #                 'actual_number': 100,

    #             })



    @api.one
    @api.depends('period_id','general_manager_id')
    def _population_number(self):
        pass

    @api.one
    @api.depends('period_id','distribution_type')
    def _get_name(self):
        self.name = self.period_id.name + '(' + self.distribution_type + ')'



class NormalDistributionItems(models.Model):
    _name = 'normal.distribution.items'
    _description = 'Normal Distribution Items'

    name = fields.Char(string='Normal Distribution Items',compute = '_get_name')
    percentage = fields.Float(string='Item Percentage')
    lower_limit = fields.Integer(string='Item Lower Limit')
    upper_limit = fields.Integer(string='Item Upper Limit')
    normal_distribution_id = fields.Many2one('normal.distribution', string="Normal Distribution")


    @api.one
    @api.depends('lower_limit','upper_limit')
    def _get_name(self):
        self.name =  '[' + str(self.lower_limit) + '-' + str(self.upper_limit) + ')'



class LineManagerPanel(models.Model):
    _name = "line.manager.panel"
    _description = "Line Manager Panel"
    

    name = fields.Char(string='Line Manager Panel', compute='_get_name')
    first_line_manager_id = fields.Many2one('hr.employee', string='First Line Manager', required=True, domain=[('state','=','onboard')])
    period_id = fields.Many2one('evaluation.period', string="Period", required=True, )
    # approval_status = fields.Boolean(string="Approval Status", related='' readonly=True, )
    evaluation_ids = fields.One2many('evaluation.evaluation','line_manager_panel_id', string="Evaluations",domain=[('state','!=','draft')])
    check_access_right = fields.Boolean(compute="_check_access",string='Access Right',readonly=True,)
    final_score_distribution_ids = fields.One2many('final.score.distribution','line_manager_panel_id', string='Final Score Distribution')
    state = fields.Selection([
        ('draft', 'Draft'),         
        ('open_for_lm_mng', 'Line Manager Evaluation'),
        ('done', 'Done')],
        string='Status', default='draft', readonly=True, compute='_get_state')

    approved_deviation = fields.Char(compute='_calculate_fifth_deviation', string="Maximum Deviation ≃")
    fifth_deviation = fields.Float(compute='_calculate_fifth_deviation',)
    fifth_deviation_count = fields.Float(compute='_calculate_fifth_deviation', string="Actual Deviation ≃")





    @api.one
    @api.depends('first_line_manager_id', 'period_id')    
    def _calculate_fifth_deviation(self):
        total_eval_number = self.env['evaluation.evaluation'].search_count([('first_line_manager_id','=',self.first_line_manager_id.id),('period_id','=',self.period_id.id),('state','!=','draft')])                
        edited_evaluation = self.env['evaluation.evaluation'].search_count([('fourth_deviation','!=',0),('first_line_manager_id','=',self.first_line_manager_id.id),('period_id','=',self.period_id.id),('state','!=','draft')])
        violation_configuration = self.env['violation.configuration'].search([('period_id','=',self.period_id.id)])

        if total_eval_number != 0:
            self.fifth_deviation_count = edited_evaluation
            # self.fifth_deviation = f"{round((edited_evaluation/total_eval_number),2) * 100}%"
            self.fifth_deviation = round((edited_evaluation/total_eval_number),2)
        else:
            self.fifth_deviation_count = 0
            self.fifth_deviation = 0
        if violation_configuration:
            self.approved_deviation = f"{math.ceil(total_eval_number * violation_configuration[0].fifth_deviation_limit)} ({violation_configuration[0].fifth_deviation_limit * 100}%)"  



    @api.model
    def create(self, values):
        evals = self.env['evaluation.evaluation'].search([('period_id','=',values.get('period_id')),('first_line_manager_id','=',values.get('first_line_manager_id')),('state','!=','draft')])
        manager_evaluation = True
        for eval in evals:
            if eval.state != 'mng_eval':
                manager_evaluation = False
                break
        violation_configuration = self.env['violation.configuration'].search([('period_id','=',values.get('period_id'))])
        if not violation_configuration:
            raise UserError('You need to set derivation configuration for the period!')    
        if not manager_evaluation:
           raise UserError('To create Line Manager Panel, all evaluations need to be in Manager Evaluation status!') 
        return super(LineManagerPanel, self).create(values)      
    @api.one
    @api.depends('first_line_manager_id', 'period_id')
    def _get_evaluation(self):
        if self.first_line_manager_id and self.period_id:
            filtered_evaluations = self.env['evaluation.evaluation'].search([('first_line_manager_id','=',self.first_line_manager_id.id),('period_id','=',self.period_id.id),('state','!=','draft')])
            print('filtered_evaluations-------------------------', filtered_evaluations)
            if filtered_evaluations:
                self.evaluation_ids = filtered_evaluations
            # else:
            #     raise UserError(_('No evaluation defined under your supervision in period %s!') %(self.period_id.name))


    @api.one
    @api.depends('period_id','evaluation_ids')
    def _get_state(self):
        if self.evaluation_ids:
            manager_signed = True
            for eval in self.evaluation_ids:
                if eval.manager_sign == False:
                    manager_signed = False
                    break

            general_manager_signed = True
            for eval in self.evaluation_ids:
                if eval.general_manager_sign == False:
                    general_manager_signed = False
                    break

            line_manager_signed = True
            for eval in self.evaluation_ids:
                if eval.lm_sign == False:
                    general_manager_signed = False
                    break    
                
            if self.period_id.evaluation_status == 'manager_assessment' and manager_signed and general_manager_signed and line_manager_signed: 
                self.state = 'done'       
            elif self.period_id.evaluation_status == 'manager_assessment' and manager_signed and general_manager_signed:
                self.state = 'open_for_gm_mng'
            else:
                self.state = 'draft'
        else:
            self.state = 'draft'        




    @api.one
    @api.depends('first_line_manager_id')
    def _check_access(self):
        if self.first_line_manager_id.id == self._uid or self.user_has_groups("ext_evaluation.group_see_all_evaluation"):
            self.check_access_right = True
        else:
            self.check_access_right = False

    @api.one
    @api.depends('first_line_manager_id','period_id')
    def _get_name(self):
        self.name =  str(self.first_line_manager_id.name) + '-' + str(self.period_id.name) 


    @api.one
    @api.depends('evaluation_ids')
    def all_line_manager_evaluated(self):
        total_eval_number = self.env['evaluation.evaluation'].search_count([('first_line_manager_id','=',self.first_line_manager_id.id),('period_id','=',self.period_id.id),('state','!=','draft')])                
        evaluated_status = True
        for rec in self.evaluation_ids:
            if rec.mng_eval_status in ('lm_edited', 'lm_unchanged'): 
                evaluated_status = True
            else:
                evaluated_status = False    
                break
        
        violation_configuration = self.env['violation.configuration'].search([('period_id','=',self.period_id.id)])
        if violation_configuration:
            if evaluated_status == True:
                if int(self.fifth_deviation_count) <= int(math.ceil(total_eval_number * violation_configuration[0].fifth_deviation_limit)):
                    for eval in self.evaluation_ids:
                        if float(eval.fourth_deviation) <= float(violation_configuration[0].fourth_deviation_limit):
                            eval.lm_evaluated()
                        else:
                            raise UserError(('The submitted score for %s is violating ±%s deviation rule!') % (eval.employee_id.name,violation_configuration[0].fourth_deviation_limit * 100))    
                else:
                    raise UserError(('The number of edited evaluations is violating +%s deviation rule!') % (violation_configuration[0].fifth_deviation_limit * 100))
            else:
                raise UserError('To approve all evaluations, evaluations sample need to be in (Line Unchanged) and (Line Edited)')                   

class ViolationConfiguration(models.Model):
    _name = 'violation.configuration'
    _description = 'Violation Configuration'

    name = fields.Char(string='Violation Configuration',)
    period_id = fields.Many2one('evaluation.period', string="Period", required=True, )
    second_deviation_limit = fields.Float(string="General Manager Score Limit")
    fourth_deviation_limit = fields.Float(string="Line Manager Score Limit")
    first_deviation_limit = fields.Float(string="General Manager Total Limit")
    fifth_deviation_limit = fields.Float(string="Line Manager Total Limit")

    @api.multi
    @api.onchange('period_id')
    def _onchange_period_id(self):
        for rec in self:
            if rec.period_id:
                rec.name = 'Violation Configuration' + ' - ' + str(rec.period_id.name)    









   