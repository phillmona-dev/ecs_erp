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

    # def generate_odoo_week_values(self):
    #     week_records = []
    #
    #     for year in range(2025, 2099):
    #         # Find first day of the year
    #         current_date = datetime(year, 1, 1)
    #
    #         # Find first Monday (weekday 0 is Monday)
    #         while current_date.weekday() != 0:
    #             current_date += timedelta(days=1)
    #
    #         # Start counting weeks from first Monday
    #         week_num = 1
    #         while current_date.year == year:
    #             # Calculate dates
    #             date_from = current_date
    #             date_to = current_date + timedelta(days=6)
    #
    #             # Create record dictionary
    #             record = {
    #                 'descr': f"{year} Week {week_num}",
    #                 'week_num': week_num,
    #                 'date_from': date_from.strftime('%Y-%m-%d'),
    #                 'date_to': date_to.strftime('%Y-%m-%d'),
    #                 'year': str(year),
    #             }
    #             week_records.append(record)
    #
    #             # Move to next week
    #             current_date += timedelta(days=7)
    #             week_num += 1
    #
    #             # Stop if we enter next year
    #             if current_date.year > year:
    #                 break
    #
    #     self.env['droga.crm.weeks'].create(week_records)