from math import radians, sin, cos, atan2, sqrt

from odoo import api, fields, models
from datetime import timedelta

from odoo.exceptions import UserError


class FleetRequest(models.Model):
    _name = "droga.fleet.request"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _description = "Droga fleet request"
    _rec_name = 'name'
    name = fields.Char(
        string='Fleet Request No.',default='NEW',
        readonly=True,
    )
    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 index=True, default=lambda self: self.env.company.id,readonly=True)
    sale_origin=fields.Many2one('sale.order')

    @api.model
    def create(self, vals_list):
        vals_list['name']=self.env['ir.sequence'].next_by_code('droga.fleet.request')
        return super().create(vals_list)

    visibility = fields.Selection([("visible", "Visible"), ("invisible", "Invisible")],default='invisible')
    cancel_reason = fields.Text(string="Cancel Reason")

    def get_requestor_id(self):
        self.requestor_id = self.env.user.id

    requestor_id = fields.Integer(compute='get_requestor_id', required=True)

    def create_string_array(self,characters):
        string_array = []
        current_string = ""

        for char in characters:
            if char == ",":
                string_array.append(current_string)
                current_string = ""
            else:
                current_string += char

        # Add the last string after the last comma (if any)
        if current_string:
            string_array.append(current_string)

        return string_array










    requested_by = fields.Many2one("res.users", string="Requested by", index=True, default=lambda self: self.env.user,readonly=True)
    date = fields.Datetime("Requested Date", default= fields.Datetime.now(), readonly=True)
    request_type = fields.Selection([ ('employee_transportation', 'Employee Transportation'),  ('resource_transportation', 'Resource Transportation') ], string='Request Type', required=True)
    purpose = fields.Char(string='Purpose')
    company = fields.Many2one('res.company', string='Company',default=lambda self: self.env.company , readonly=True)
    department = fields.Many2one('hr.department', string='Department',default=lambda self: self.env.user.department_id, readonly=True)
    status = fields.Selection( [("draft", "Draft"), ("submitted", "submitted"), ("approved", "Approved"),("queued", "Queued"),("assigned", "Assigned"), ("completed", "Completed"),("cancelled", "Cancelled")], default='draft',tracking=True,required=True)

    def get_delivered_to(self):
        for req in self:
            result = ""
            if req.create_uid == self.env.user.id:

                for partner in req.task_ids:
                        delivered_to = partner.delivered_to
                        name = str(partner.name)
                        if delivered_to != False:
                            result = result + str(delivered_to.name) + ","

                req.delivered_to = result
            else:
                req.delivered_to = result

    def get_requested_for(self):
        for req in self:
            result = ""
            if req.requested_by.id == self.env.user.id:

                for task in req.task_ids:
                    if task.requested_for:
                        result = result + str(task.requested_for.name) + ","
                    else:
                        result = result + str(task.delivered_to.name) + ","
                req.requested_for = result
            else:
                req.requested_for = result



    def get_travel_log(self):
        for req in self:
            result = ""
            if req.requested_by.id == self.env.user.id:

                for partner in req.task_ids:
                    if (partner.from_location != False or partner.to_location ):
                        result = result + str(partner.from_location) + " to " + str(partner.to_location) + ","
                req.travel_log = result
            else:
                req.travel_log = result



    def get_vehicle_used(self):
        for req in self:
            result = ""
            if req.requested_by.id == self.env.user.id:

                for partner in req.task_ids:
                    if (partner.vehicle != False):
                        result = result + str(partner.vehicle.license_plate) + ","
                req.vehicle_used = result
            else:
                req.vehicle_used = result


    def get_resource_name(self):
        for req in self:
            result = ""
            if req.requested_by.id == self.env.user.id:

                for partner in req.task_ids:
                    if (partner.resource_name != False):
                        result = result + str(partner.resource_name) + ","
                req.resource_name = result
            else:
                req.resource_name = result



    def get_amount(self):
        for req in self:
            result = ""
            if req.requested_by.id == self.env.user.id:

                for partner in req.task_ids:
                    if (partner.amount != False):
                        result = result + str(partner.amount) + ","
                req.amount = result
            else:
                req.amount = result


    def get_chauffeur(self):
        for req in self:
            result = ""
            if req.requested_by.id == self.env.user.id:

                for partner in req.task_ids:
                    if (partner.chauffeur != False):
                        result = result + str(partner.chauffeur.name) + ","
                req.chauffeur = result
            else:
                req.chauffeur = result




    delivered_to = fields.Char(string='Delivered To', compute='get_delivered_to',required=True)

    requested_for = fields.Char(string='Requested For', compute='get_requested_for', required=True)
    resource_name = fields.Char(string='Resource Transported', compute='get_resource_name',required=True)
    amount = fields.Char(string='Quantity', compute='get_amount',required=True)
    chauffeur = fields.Char(string='Chauffeur', compute='get_chauffeur',required=True)
    vehicle_used = fields.Char(string='Vehicle Used', compute='get_vehicle_used',required=True)
    travel_log = fields.Char(string='Travel Log', compute='get_travel_log',required=True)
    distance_on_delivery = fields.Char('Distance on Delivery', readonly=True, default='Pending')



    # RELATIONS
    task_ids = fields.One2many('droga.fleet.request.task', 'request_id',string='Request Detail',tracking=True)


    def set_activity_done(self):
        activity = self.env["mail.activity"].search(
            [('res_name', '=', self.name)])
        if activity:
            activity.sudo().action_done()

    def get_users_for_roles(self, role, company_id):
        users = []
        roles = self.env['res.groups'].search([('name', '=', role)])

        for user in roles.users:
            if user.company_id.id == company_id:
                users.append(user.id)
        return users

    def create_activity_assign(self, user_id):
        # create mail activity for the approval
        todos = dict(res_id=self.id,
                     res_model_id=self.env['ir.model'].search([('model', '=', 'droga.fleet.request')]).id,
                     user_id=user_id, summary='Assign Driver', note='Assign Driver',
                     activity_type_id=4,
                     date_deadline=fields.datetime.now())

        self.env['mail.activity'].sudo().create(todos)


    def create_activity(self, user_id):
        # create mail activity for the approval
        todos = dict(res_id=self.id,
                     res_model_id=self.env['ir.model'].search([('model', '=', 'droga.fleet.request')]).id,
                     user_id=user_id, summary='Grant Approval', note='Incoming fleet',
                     activity_type_id=4,
                     date_deadline=fields.datetime.now())

        self.env['mail.activity'].sudo().create(todos)
    def create_activity_reverse(self, user_id):
        # create mail activity for the approval
        todos = dict(res_id=self.id,
                     res_model_id=self.env['ir.model'].search([('model', '=', 'droga.fleet.request')]).id,
                     user_id=user_id, summary='Fleet Request Approval', note='Fleet Request Approval',
                     activity_type_id=4,
                     date_deadline=fields.datetime.now())

        self.env['mail.activity'].sudo().create(todos)

    def notify(self, message,user):
        self.env['bus.bus']._sendone(user, "simple_notification", {
            "title": "Fleet Request Status Update.",
            "message": message,
            "sticky": True,
            "warning": True
        })

    def set_to_cancel(self):
        self.status = 'cancelled'





    def sale_order_fleet_request(self):
        if (self.task_ids.requested_for or self.delivered_to ):
            if self.requested_by == 'resource_transportation':
                if not (self.task_ids.resource_name or self.task_ids.amount):
                    raise UserError('Please fill in all the fields in the form.')
            if not (self.task_ids.from_location or self.task_ids.to_location or self.task_ids.service_time):
                raise UserError('Please fill in all the fields in the form.')
            else:
                print('act')
                self.status = 'submitted'
                users = self.get_users_for_roles('Fleet Manager', self.company_id.id)
                for user in users:
                    self.create_activity_reverse(user)
        else:
            raise UserError('Please fill in all the fields in the form.')



    def submit_fleet_request(self):
        if (self.task_ids.requested_for or self.task_ids.delivered_to ):
            if self.requested_by == 'resource_transportation':
                if not (self.task_ids.resource_name or self.task_ids.amount):
                    raise UserError('Please fill in The Resource to transport and the Quantity.')
            if not (self.task_ids.from_location or self.task_ids.to_location or self.task_ids.service_time):
                raise UserError('Please fill in the required location and time fields.')
            else:
                print('act')
                self.status = 'submitted'
                users = self.get_users_for_roles('Fleet Manager', self.company_id.id)
                for user in users:
                    self.create_activity_reverse(user)
        else:
            raise UserError('Please fill in the Employee requiring transport or the Partner to Deliver to.')

    def cancel_submit_request(self):
        self.set_activity_done()
        return {
            'name': 'Cancel Request',
            'view_mode': 'form',
            'res_model': 'cancel.reason.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_users': self.requested_by.id,
                'default_request_num':self.name,
            }

        }


    def accept_request(self):

        self.status = 'approved'


    def reject_request(self):
        self.set_activity_done()
        return {
            'name': 'Cancel Request',
            'view_mode': 'form',
            'res_model': 'cancel.reason.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_users': self.requested_by.id,
                'default_request_num': self.name,
            }

        }


    def driver_assigned(self):
        if not (self.task_ids.chauffeur or self.task_ids.vehicle):
            raise UserError('Please fill in all the fields in the form.')
        else:
            plate = self.task_ids.vehicle.license_plate
            vehicle_status = self.env['fleet.vehicle'].search([('license_plate', '=' , plate)])
            vehicle_status.set_false()
            self.status = 'assigned'
            print(self.delivered_to)
            message = "Fleet Request Has been assigned accepted successfully."
            self.notify(message, self.create_uid)

    def driver_assigned_queue(self):
        if not (self.task_ids.chauffeur or self.task_ids.vehicle):
            raise UserError('Please fill in all the fields in the form.')
        else:
            vehicle_status = self.env['fleet.vehicle'].search(
                [('licence_plate', '=', self.task_ids.vehicle.licence_plate)])
            vehicle_status.set_false()
            self.status = 'assigned'
            print(self.delivered_to)
            message = "Fleet Request Has been assigned accepted successfully."
            self.notify(message, self.create_uid)

    def reject_driver_queue(self):
        self.set_activity_done()
        return {
            'name': 'Cancel Request',
            'view_mode': 'form',
            'res_model': 'cancel.reason.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_users': self.requested_by.id,
                'default_request_num': self.name,
            }

        }

    def reject_driver(self):
        self.set_activity_done()
        return {
            'name': 'Cancel Request',
            'view_mode': 'form',
            'res_model': 'cancel.reason.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_users': self.requested_by.id,
                'default_request_num': self.name,
            }

        }



    def await_driver(self):
        self.status='queued'
        self.notify("Waiting For Driver To Be Assigned", self.create_uid)

    def completed(self):
        self.set_activity_done()
        self.status = 'completed'
        message = "Your fleet Request has been successfully completed."
        self.notify(message, self.create_uid)


    def delete_record(self):
            self.unlink()




class RequestTasks(models.Model):
    _name = "droga.fleet.request.task"
    _description = "Droga fleet request task"

    name= fields.Char('Name')
    fleet_request_id = fields.Many2one('droga.fleet.request', string="Fleet Request")

    def get_dep_id(self):
        department_id = self.env.user.department_id.id
        self.dep_id = department_id
    dep_id = fields.Integer(compute='get_dep_id',required=True)

    requested_for = fields.Many2one('hr.employee',
                                    string='Requested For',
                                    domain="[('department_id', '=', dep_id)]",tracking=True)

    delivered_to = fields.Many2one('res.partner', String='Deliver To',tracking=True)
    driver_assigned = fields.Many2one("hr.employee", string="Assigned Driver",
                                      domain="[('department_id.name', '=', 'Drivers')]")
    status = fields.Selection( [("draft", "Draft"), ("submitted", "Submitted"), ("approved", "Approved"),("assigned", "Assigned"),("completed", "Completed"),("canceled", "Canceled")], default='draft',tracking=True,  related='fleet_request_id.status')

    request_id = fields.Many2one('droga.fleet.request')
    request_type = fields.Selection([
        ('employee_transportation', 'Employee Transportation'),
        ('resource_transportation', 'Resource Transportation')
    ], string='Request Type', required=True,related='request_id.request_type')

    resource_name = fields.Char(String='Resource to be Transported',tracking=True)
    amount = fields.Integer(String='Quantity',tracking=True)
    deliver_to = fields.Many2one('res.partner', string='Deliver To',tracking=True)

    delivered=fields.Boolean('Delivered',default=False)


    #COMMON
    comment = fields.Text("Comment")
    service_time = fields.Datetime("Time For Service",tracking=True)
    from_location = fields.Char(string='From Location',tracking=True)
    to_location = fields.Char(string='To Location',tracking=True)

    def travel_log(self):
        t_log = str(self.from_location) + ' To ' + str(self.to_location)
        return  t_log

    travel_log = fields.Text(compute='travel_log', string='Travel Log', required=True)

    vehicle = fields.Many2one('fleet.vehicle', string='Assign Vehicle')


    #EMPLOYEE
    requested_for = fields.Many2one('hr.employee',string='Requested For', domain="[('department_id', '=', 'self.env.user.department_id.id')]")

    chauffeur = fields.Many2one("hr.employee", string=" Driver (If Needed)",
                                domain="[('department_id.name', '=', 'Drivers')]")

    request_id = fields.Many2one('droga.fleet.request')




class CancelReasonWizard(models.TransientModel):
    _name = 'cancel.reason.wizard'

    reason = fields.Text(string="Reason")
    fleet_request = fields.Many2one('droga.fleet.request', string="Fleet Request")

    users = fields.Integer(string='User to Notify')
    request_num = fields.Char(string='Request Number')

    def notify(self, message,user):
        self.env['bus.bus']._sendone(user, "simple_notification", {
            "title": "Fleet Request Status Update.",
            "message": message,
            "sticky": True,
            "warning": True
        })
        print('notify')

    def confirm_cancel(self):
        active_id = self.env.context.get('active_id')
        if active_id:
            request = self.env['droga.fleet.request'].browse(active_id)
            request.cancel_reason = self.reason
        self.notify(self.reason, self.users)

        req = self.env['droga.fleet.request'].search([('name', '=', self.request_num)])
        req.set_to_cancel()
        return {'type': 'ir.actions.act_window_close'}

    def cancel(self):
        self.notify(self.reason ,self.users)
        return {'type': 'ir.actions.act_window_close'}










