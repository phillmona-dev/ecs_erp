from odoo import fields, models
class DrogaProject(models.Model):
    _inherit = 'project.project'
    isinterest= fields.Boolean(string="Is intest has interest?", compute='_compute_isinterest')
    isactive= fields.Boolean(string="Active?")
    droga_companies = fields.Many2one('res.company', string='Sister Companies', required=True, default=lambda self: self.env.company)
   
    
    # _name='droga.project'
    #droga_companies=fields.Many2one('res.company', string="Sister Company",copy=True)
    droga_parent_project=fields.Many2one( 'droga.parent.project',string='Parent Project',copy=True)
    droga_project_type=fields.Many2one('droga.project.type', string="Project Type",copy=True)



   
    
class DrogaParentProject(models.Model):
    _name = 'droga.parent.project'
    #_description = "This model is used to catagoraize difrent type of loan"

    name=fields.Char('parent Project', required=True)
    

class DrogaProjectType(models.Model):
    _name = 'droga.project.type'
    #_description = "This model is used to catagoraize difrent type of loan"

    name=fields.Char('Drpga Project type', required=True)

