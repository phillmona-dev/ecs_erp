from odoo import models, fields, api


class droga_tender_master_related(models.Model):
    _inherit='droga.tender.master'
    cus_type = fields.Many2one(related='customer.cust_type_ext', string='Customer type',store=True)
    phone_add = fields.Char(related='customer.phone', string='Phone number')
    awarded_amt_total=fields.Float('Awarded total amount',compute='_compute_awarded_amt_total',store=True)
    performance_amt_sent=fields.Float('Amount sent',compute='_compute_amt_performance',store=True)
    performance_amt_award=fields.Float('Amount awarded',compute='_compute_amt_performance',store=True)
    performance_pct=fields.Float('Percentage performance',compute='_compute_amt_performance',store=True)
    award_folder=fields.Char(related='detail_submissions_fin.award_fold_num')
    item_types=fields.Text('Item / types',compute='_get_item_types')
    tender_amt_participated=fields.Float('Amount participated',compute='_compute_awarded_amt_total')

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
            amount = 0
            awarded_cost = 0
            det_performance = rec.detail_performance
            for perf_line in det_performance:
                amount += perf_line['amount']
                awarded_cost += perf_line['award_cost']
            rec.performance_amt_sent = amount
            rec.performance_amt_award = awarded_cost
            rec.performance_pct=(awarded_cost/amount)*100 if amount!=0 else 0

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

