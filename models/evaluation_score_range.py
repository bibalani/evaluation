# -*- coding: utf-8 -*-

from cmath import nan
import string
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import time


class RangeCategory(models.Model):
    _name = "range.category"
    _description = "Range Category"
    

    name = fields.Char(string='Range Name', compute='_get_name')
    period_id = fields.Many2one('evaluation.period', string = "Period",required = True)
    is_active = fields.Boolean(string="Active")
    range_category_items_ids = fields.One2many('range.category.items', 'range_category_id', string="Range and Corrosponding Weight", store=True)

    @api.one
    @api.depends('period_id')
    def _get_name(self):
        if not self.period_id:
            self.name = ''
        else:    
            self.name = 'Range Category'+ ' (' + str(self.period_id.name) + ')'

       
    @api.one
    def generate_score_range_calculation(self):
        self.env.cr.execute("""DELETE FROM score_range_calculation WHERE period_id = {self.period_id.id}""".format(**locals()))
        if self.is_active:
            defined_range_category_items = self.env.cr.execute("""SELECT * from range_category_items WHERE range_category_id = %s""",(self.id,))
            defined_range_category_items = self.env.cr.fetchall()
            # defined_range_category_items = self.env['range.category.items'].search([('range_category_id','=',self.id)])
            print('defined_range_category_items------------->',defined_range_category_items)

            line_manager_list = self.env.cr.execute("""SELECT DISTINCT first_line_manager_id from evaluation_evaluation WHERE period_id = %s""",(self.period_id.id,))
            line_manager_list = self.env.cr.fetchall()
            # line_manager_list = self.env['evaluation.evaluation'].search([('period_id','=',self.period_id.id)])
            print('line_manager_list-------->',line_manager_list)
                                                    
            if defined_range_category_items:
                for lm in line_manager_list:
                    for item in defined_range_category_items:
                        self.sudo().env['score.range.calculation'].create({
                        'range_category_id':self.id,
                        'period_id':self.period_id.id,
                        'range_category_item_id':item[0],
                        'first_line_manager_id':lm[0],
                        # 'average_score': fix_item.target,
                        'lb': item[2],
                    })
 
            else:
               raise UserError('Please set range category item(s) for this period first!')  
        return True         


    @api.one
    @api.constrains('range_category_items_ids')
    def _check_total_weight(self):
        total = 0.0
        category_items = self.range_category_items_ids
        for obj in category_items:
            total += obj.weight
        if total < 100 or total > 100:
            raise ValidationError(_('Total weights on each range category must be 100 %.'))
        else :
            return True

    @api.one
    @api.constrains('range_category_items_ids')
    def _check_range_overlap(self):
        category_items = self.range_category_items_ids
        for i in range(len(category_items)-1):
            if (category_items[i].lower_bound >= category_items[i].upper_bound) or (category_items[i].upper_bound > category_items[i+1].lower_bound):
                raise ValidationError(_('There might be some overlap between defined ranges.'))
        else :
            return True        

class RangeCategoryItems(models.Model):
    _name = "range.category.items"
    _description = "Range Category Items"

    name = fields.Char(string='Range Items Name', compute='_get_name')
    weight = fields.Float(string="Weight")
    lower_bound = fields.Float(string="Lower Bound")
    upper_bound = fields.Float(string="Upper Bound")
    range_category_id = fields.Many2one('range.category', string="Range Category")
    # is_active = fields.Boolean(string="Active")

    @api.one
    @api.depends('lower_bound','upper_bound')
    def _get_name(self):
        self.name =  '[' + str(self.lower_bound) + '-' + str(self.upper_bound) + ')'


    


class ScoreRangeCalculation(models.Model):
    _name = 'score.range.calculation'
    _description = "Score Range Calculation"

#   related
    range_category_id = fields.Many2one('range.category', string='Score Range')
    period_id = fields.Many2one(related='range_category_id.period_id', string = "Period", required = True, store=True,)
    range_category_item_id = fields.Many2one('range.category.items', string="Range Category Item")
    first_line_manager_id = fields.Many2one('hr.employee', string="First Line Manager", required=True,domain=[('state','=','onboard')])   
    average_score = fields.Float(compute = '_average_line_score', readonly=True, string="Average Line Score", store=True)
    lb = fields.Float(related='range_category_item_id.lower_bound', required=True, store=True,)


    @api.model
    def create(self, values):
        score_range_rec = self.env['score.range.calculation'].search([('range_category_item_id', '=', values.get('range_category_item_id')),
                                                                      ('first_line_manager_id','=',values.get('first_line_manager_id'))])
        if not score_range_rec:
            return super(ScoreRangeCalculation, self).create(values)
        else:    
            raise UserError(_('Calculation for %s within %s score range has been already done!') % (score_range_rec.first_line_manager_id.name, score_range_rec.range_category_item_id.name))


    

    @api.multi
    @api.depends('period_id','first_line_manager_id','range_category_item_id.lower_bound','range_category_item_id.upper_bound')
    def _average_line_score(self):
        for rec in self:
            if rec.period_id.id and rec.first_line_manager_id.id and rec.range_category_item_id.lower_bound >=0 and rec.range_category_item_id.upper_bound:
                    
                range_count = rec.env.cr.execute("""select count(*) from evaluation_evaluation where period_id = {rec.period_id.id}
                                                    and first_line_manager_id = {rec.first_line_manager_id.id} and final_score >= {rec.range_category_item_id.lower_bound}
                                                    and final_score < {rec.range_category_item_id.upper_bound}""".format(**locals()))
                n = self.env.cr.fetchone()[0]  
                
                
                total_count = rec.env.cr.execute("""select count(*) from evaluation_evaluation where period_id = %s and
                                                    first_line_manager_id = %s and final_score>= %s""",
                                                    (rec.period_id.id,rec.first_line_manager_id.id,0,))
                m = rec.env.cr.fetchone()[0]                    
                score = [n/m if m!=0 else 0]
                rec.average_score = score[0] * 100 
 


    @api.multi
    @api.onchange('range_category_id')
    def onchange_range_category_id(self):
        filtered_range_items = []
        filtered_range_items_ids  = []
        if self.range_category_id:
            print('self.range_category_id----->',self.range_category_id)
            filtered_range_items = self.env['range.category.items'].search([('range_category_id','=',self.range_category_id.id),('is_active','=',True)])
            print('-------------->',filtered_range_items)
            filtered_range_items_ids = [x.id for x in filtered_range_items]
            print('filtered_range_items_ids---',filtered_range_items_ids)
        return {'domain': {'range_category_item_id': [('id', 'in', filtered_range_items_ids)]}} 



   






