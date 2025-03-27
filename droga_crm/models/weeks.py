from odoo import models,fields
from datetime import datetime, timedelta

class CrmWeeks(models.Model):
    _name='droga.crm.weeks'
    _rec_name = 'descr'
    descr=fields.Char('Description')
    week_num=fields.Integer('Week Number')
    date_from=fields.Date('Date from')
    date_to = fields.Date('Date from')
    year=fields.Char('Year')
    long_descr=fields.Char('Description')

    @staticmethod
    def find_week_record(self,search_date=None):
        """
        Find or create the week record for the specified date
        Returns the record ID
        """
        if search_date is None:
            search_date = fields.Date.today()
        elif isinstance(search_date, str):
            search_date = datetime.strptime(search_date, '%Y-%m-%d')
        elif isinstance(search_date, datetime):
            search_date = search_date.date()

        # Search for existing record
        week = self.env['droga.crm.weeks'].search([
            ('date_from', '<=', search_date),
            ('date_to', '>=', search_date)
        ], limit=1)

        if week:
            return week.id

        # If not found, you might want to create it (optional)
        # This part would depend on your business logic
        return False

    @staticmethod
    def get_next_week(self, search_date=None):
        if search_date is None:
            search_date = fields.Date.today() +timedelta(days=7)
        elif isinstance(search_date, str):
            search_date = datetime.strptime(search_date, '%Y-%m-%d')+timedelta(days=7)
        elif isinstance(search_date, datetime):
            search_date = search_date.date()+timedelta(days=7)

        # Search for existing record
        week = self.env['droga.crm.weeks'].search([
            ('date_from', '<=', search_date),
            ('date_to', '>=', search_date)
        ], limit=1)

        if week:
            return week.id

        # If not found, you might want to create it (optional)
        # This part would depend on your business logic
        return False

    def update_weeks_info(self):
        prev=self.env['droga.crm.weeks'].find_week_record(self,fields.Date.today() +timedelta(days=-7))
        current = self.env['droga.crm.weeks'].find_week_record(self)
        next = self.env['droga.crm.weeks'].get_next_week(self)
        visits=self.env['droga.customer.visit.header'].search([('weeks','in',(prev,current,next))])
        for vi in visits:
            if vi.weeks.id==prev:
                vi.visit_header=vi.weeks.long_descr
            elif vi.weeks.id==current:
                vi.visit_header = 'Current Plan - ' + vi.weeks.long_descr
            else:
                vi.visit_header = 'Next Plan - ' + vi.weeks.long_descr
