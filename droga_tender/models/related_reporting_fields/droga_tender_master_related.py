from odoo import models, fields, api
import datetime


class droga_tender_master_related(models.Model):
    _inherit='droga.tender.master'
    cus_type = fields.Many2one(related='customer.customer_type', string='Customer type',store=True)
    phone_add = fields.Char(related='customer.master_cust_id.phone', string='Phone number')
    awarded_amt_total=fields.Float('Awarded total amount',compute='_compute_awarded_amt_total',store=True)
    performance_amt_sent=fields.Float('Total Quotation',compute='_compute_amt_performance',store=True)
    performance_amt_award=fields.Float('Total award',compute='_compute_amt_performance',store=True)
    performance_pct=fields.Float('Percentage performance',compute='_compute_amt_performance',store=True)
    award_folder=fields.Char(related='detail_submissions_fin.award_fold_num')
    item_types=fields.Text('Item / types',compute='_get_item_types')
    tender_amt_participated=fields.Float('Total Quotation',compute='_compute_awarded_amt_total')

    #Alert booleans
    submission_alert_sent=fields.Boolean('Submission alert sent status')
    opening_alert_sent = fields.Boolean('Opening alert sent status')
    extension_alert_sent = fields.Boolean('Extension alert sent status')

    @api.depends('detail_submissions_fin.amount','detail_submissions_fin.status')
    def _compute_awarded_amt_total(self):
        for rec in self:
            fin_details = rec.detail_submissions_fin
            amount = 0
            amt_participated=0
            for fin_line in fin_details:
                amt_participated+=fin_line['amount']
                if fin_line['status']=='awarded':
                    amount += fin_line['amount']
            rec.awarded_amt_total = amount
            rec.tender_amt_participated=amt_participated

    @api.depends('detail_performance.amount', 'detail_performance.award_cost')
    def _compute_amt_performance(self):
        for rec in self:
            awarded_cost = 0
            det_performance = rec.detail_performance
            for perf_line in det_performance:
                awarded_cost += perf_line['award_cost']
            rec.performance_amt_award = awarded_cost
            rec.performance_pct=(float(rec.performance_amt_award/rec.tender_amt_participated) )*100 if rec.tender_amt_participated!=0 else 0

    @api.depends('detail_tenders.lot_number','detail_tenders.type_item')
    def _get_item_types(self):
        for rec in self:
            type_item=''
            for det_tend in rec.detail_tenders:
                #type_item=type_item+'\nLot '+det_tend.lot_number+' - ' if type_item!='' else 'Lot '+det_tend.lot_number+' - '
                type_item = type_item.rstrip(type_item[-1]).rstrip(type_item[-2]) + '\nLot ' + det_tend.lot_number + ' - ' if type_item != '' else 'Lot ' + det_tend.lot_number + ' - '
                for item_de in det_tend.type_item:
                    type_item=type_item+item_de.type_or_item_name+', '
            rec.item_types=type_item.rstrip(type_item[-1]).rstrip(type_item[-2]) if type_item != '' else type_item

    def _run_alert_scheduler(self):
        for rec in self:
            rec.submission_alert_sent=False
            rec.extension_alert_sent = False
        tender_users = self.env['res.groups'].search([('name', '=', 'Tender User')])[0]['users']

        # region submission alerts
        compare_date_addis = datetime.date.today() + datetime.timedelta(days=3)
        compare_date_other = datetime.date.today() + datetime.timedelta(days=5)
        recs = self.env['droga.tender.master'].search([('submission_alert_sent', '=', False),
                                                       ('closing_date_gre', '<', compare_date_addis),
                                                       ('bid_submit_place.submission_place_name', '=ilike', 'addis')])
        for rec in recs:
            descr = 'Tender submission, 3 days left for ' + rec['ten_name']
            rec['submission_alert_sent'] = True
            if rec['closing_date_gre'] == rec['open_date_gre']:
                rec['opening_alert_sent'] = True
            for ten_user in tender_users:
                self.env['mail.activity'].sudo().create({
                    'res_model_id': self.env.ref('droga_tender.model_droga_tender_master').id,
                    'res_name': descr,
                    'res_id': rec.id,
                    'automated': True,
                    'user_id': ten_user.id,
                    'date_deadline': rec['closing_date_gre'],
                    'activity_type_id': self.env['mail.activity.type'].search(
                        [('name', 'like', '%Tender submission%')]).id,
                    'summary': descr,
                    'note': rec['ten_name']
                })
        recs = self.env['droga.tender.master'].search([('submission_alert_sent', '=', False),
                                                       ('closing_date_gre', '<', compare_date_other), (
                                                           'bid_submit_place.submission_place_name', 'not ilike',
                                                           'Addis')])
        for rec in recs:
            descr = 'Tender submission, 5 days left for ' + rec['ten_name']
            rec['submission_alert_sent'] = True
            if rec['closing_date_gre'] == rec['open_date_gre']:
                rec['opening_alert_sent'] = True
            for ten_user in tender_users:
                self.env['mail.activity'].sudo().create({
                    'res_model_id': self.env.ref('droga_tender.model_droga_tender_master').id,
                    'res_name': descr,
                    'res_id': rec.id,
                    'automated': True,
                    'user_id': ten_user.id,
                    'date_deadline': rec['closing_date_gre'],
                    'activity_type_id': self.env['mail.activity.type'].search(
                        [('name', 'like', '%Tender submission%')]).id,
                    'summary': descr,
                    'note': rec['ten_name']
                })
        # endregion

        # region open date alerts
        compare_date = datetime.date.today() + datetime.timedelta(days=1)
        recs = self.env['droga.tender.master'].search([('opening_alert_sent', '=', False),
                                                       ('open_date_gre', '<', compare_date)])
        for rec in recs:
            descr = 'Tender open date, 1 day left for ' + rec['ten_name']
            rec['opening_alert_sent'] = True

            for ten_user in tender_users:
                self.env['mail.activity'].sudo().create({
                    'res_model_id': self.env.ref('droga_tender.model_droga_tender_master').id,
                    'res_name': descr,
                    'res_id': rec.id,
                    'automated': True,
                    'user_id': ten_user.id,
                    'date_deadline': rec['open_date_gre'],
                    'activity_type_id': self.env['mail.activity.type'].search(
                        [('name', 'like', '%Tender opening%')]).id,
                    'summary': descr,
                    'note': rec['ten_name']
                })
        # endregion

        # region extension date alerts
        compare_date_addis = datetime.date.today() + datetime.timedelta(days=3)
        compare_date_other = datetime.date.today() + datetime.timedelta(days=5)
        recs = self.env['droga.tender.master'].search([('extension_alert_sent', '=', False),
                                                       ('extension_date_gre', '<', compare_date_addis),
                                                       ('bid_submit_place.submission_place_name', '=ilike',
                                                        'addis')])
        for rec in recs:
            descr = 'Tender extended submission, 3 days left for ' + rec['ten_name']
            rec['extension_alert_sent'] = True
            if rec['extension_date_gre'] == rec['open_date_gre']:
                rec['opening_alert_sent'] = True
            for ten_user in tender_users:
                self.env['mail.activity'].sudo().create({
                    'res_model_id': self.env.ref('droga_tender.model_droga_tender_master').id,
                    'res_name': descr,
                    'res_id': rec.id,
                    'automated': True,
                    'user_id': ten_user.id,
                    'date_deadline': rec['extension_date_gre'],
                    'activity_type_id': self.env['mail.activity.type'].search(
                        [('name', 'like', '%Tender submission%')]).id,
                    'summary': descr,
                    'note': rec['ten_name']
                })
        recs = self.env['droga.tender.master'].search([('extension_alert_sent', '=', False),
                                                       ('extension_date_gre', '<', compare_date_other),
                                                       ('bid_submit_place.submission_place_name', 'not ilike',
                                                        'addis')])
        for rec in recs:
            descr = 'Tender extended submission, 5 days left for ' + rec['ten_name']
            rec['submission_alert_sent'] = True
            if rec['extension_date_gre'] == rec['open_date_gre']:
                rec['opening_alert_sent'] = True
            for ten_user in tender_users:
                self.env['mail.activity'].sudo().create({
                    'res_model_id': self.env.ref('droga_tender.model_droga_tender_master').id,
                    'res_name': descr,
                    'res_id': rec.id,
                    'automated': True,
                    'user_id': ten_user.id,
                    'date_deadline': rec['extension_date_gre'],
                    'activity_type_id': self.env['mail.activity.type'].search(
                        [('name', 'like', '%Tender submission%')]).id,
                    'summary': descr,
                    'note': rec['ten_name']
                })
        # endregion


