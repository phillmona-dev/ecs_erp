from datetime import datetime, date, time
from pydoc import classname
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError


from odoo import api, fields, models
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError
from odoo.tools.convert import RecordDictWrapper


class AccountLoanConst(models.Model):
    _inherit = 'account.loan'

    @api.constrains('interest_start_date', 'contract_date', 'payment_start_date',
                    'loan_repayment_ids', 'loan_receipt_ids', 'payment', 'loan_amount')
    def _check_date(self):
        for loans in self:
            current_date = datetime.today()
            cday = current_date.date()
            recipts=0
            for recipt in loans.loan_receipt_ids:
                recipts+=recipt.receipt
            if recipts>loans.loan_amount:
                raise ValidationError(
                    "The receipts cannot be greater than the Loan amount")

            

            # if isinstance(record.id, models.NewId):
            if loans.contract_date > loans.payment_start_date:
                raise ValidationError(
                    "The Payment start date cannot be set in the past of the contract date")

            # if not loans.interest_start_date:
                #raise ValidationError("Please insert the first receipt")
            if loans.interest_start_date:
                if loans.contract_date > loans.interest_start_date:
                    raise ValidationError(
                        "The Interest Start Date cannot be set in the past of The Contract Date")
                if loans.interest_start_date > loans.payment_start_date:
                    raise ValidationError(
                        "The Payment start date cannot be set in the past the first receipt date")
            if loans.contract_date > cday:
                raise ValidationError(
                    "The Contract Date cannot be set in the Future")

            if loans.loan_amount <= 0:
                raise ValidationError("Please enter the proper Loan Amount")
            if loans.anual_interest_rate <= 0 or loans.anual_interest_rate >100:
                raise ValidationError(
                    "Please enter the proper amount of Anual Interst Rate %(1-100)")
            if loans.payment_month <= 0:
                raise ValidationError(
                    "Please enter the proper amount of Payment Ranage in Month ")

            if loans.payment <= 0:
                raise ValidationError(
                    "Please enter the proper amount of Payment Amount per Period ")

            if loans.loan_period_year <= 0:
                raise ValidationError(
                    "Please enter the proper Period in years ")
            for payments in loans.loan_repayment_ids:
                if payments.value_date:
                    if payments.value_date < loans.contract_date:
                        raise ValidationError(
                            "The payment Date can not be in the past of Contract Date ")
                    if payments.value_date < loans.interest_start_date:
                        raise ValidationError(
                            "The payment Date can not be in the past of The first recipt")
                # if payments.value_date<loans.anual_interest_rate:
                #     raise ValidationError("The First recipt Date can not be in the past of payment Date")

            for payments in loans.loan_receipt_ids:
                if payments.value_date:
                    if payments.value_date < loans.contract_date:
                        raise ValidationError(
                            "The Contract Date can not be in the past of Recipt Date")

            # if loans.contract_date>loans.loan_repayment_ids.value_date:
            #     raise ValidationError("The Value Date cannot be set in the past of The Contract Date ")
            # if loans.contract_date>loans.loan_receipt_ids.value_date:
            #     raise ValidationError("The Value Date cannot be set in the past of TheContract Date")
