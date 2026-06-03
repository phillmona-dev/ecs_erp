# -*- coding: utf-8 -*-
import json
import logging
from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)

class EcsAttendanceApiController(http.Controller):
    """
    REST controller exposing JSON endpoints for attendance log imports and profile retrieval.
    """

    def _validate_token(self):
        token = request.httprequest.headers.get('Authorization') or request.httprequest.args.get('token')
        if not token:
            return False
        # Strip "Bearer " if present
        if token.startswith("Bearer "):
            token = token[7:]
            
        sys_token = request.env['ir.config_parameter'].sudo().get_param('ecs_api.secret_token', 'default_ecs_secure_api_token')
        return token == sys_token

    @http.route('/api/v1/attendance/push', type='json', auth='none', methods=['POST'], csrf=False)
    def push_attendance(self, **kwargs):
        """
        Receives biometric terminal attendance logs.
        Payload structure:
        {
            "records": [
                {
                    "employee_pin": "EMP001",
                    "time": "2026-05-30 08:30:00",
                    "action": "check_in"
                }
            ]
        }
        """
        if not self._validate_token():
            return {
                'status': 'error',
                'message': 'Unauthorized. Invalid API Secret Token.'
            }

        # JSON RPC automatically parses JSON body into kwargs
        records = kwargs.get('records', [])
        if not records:
            return {
                'status': 'error',
                'message': 'No attendance records provided in payload.'
            }

        created_count = 0
        skipped_records = []

        # Iterate and create logs in superuser mode
        for rec in records:
            pin = rec.get('employee_pin')
            time_str = rec.get('time')
            action = rec.get('action') # check_in or check_out

            if not pin or not time_str or not action:
                skipped_records.append({'record': rec, 'reason': 'Missing pin, time, or action.'})
                continue

            # Find employee by PIN or barcode
            employee = request.env['hr.employee'].sudo().search([
                '|', ('barcode', '=', pin), ('pin', '=', pin)
            ], limit=1)
            
            if not employee:
                skipped_records.append({'record': rec, 'reason': 'Employee not found.'})
                continue

            try:
                # Convert time string to standard Odoo Datetime field representation (UTC format)
                log_time = fields.Datetime.from_string(time_str)
                
                # Check for existing logs to avoid duplication
                existing = request.env['ecs.hr.attendance'].sudo().search([
                    ('employee_id', '=', employee.id),
                    ('attendance_date', '=', log_time.date()),
                ], limit=1)
                
                if existing:
                    if action == 'check_in' and not existing.check_in:
                        existing.check_in = log_time
                    elif action == 'check_out' and not existing.check_out:
                        existing.check_out = log_time
                else:
                    vals = {
                        'employee_id': employee.id,
                        'attendance_date': log_time.date(),
                        'check_in': log_time if action == 'check_in' else False,
                        'check_out': log_time if action == 'check_out' else False,
                    }
                    request.env['ecs.hr.attendance'].sudo().create(vals)
                
                created_count += 1
            except Exception as e:
                _logger.error("Failed to process attendance record %s: %s", rec, str(e))
                skipped_records.append({'record': rec, 'reason': str(e)})

        return {
            'status': 'success',
            'processed_count': created_count,
            'skipped_count': len(skipped_records),
            'skipped_records': skipped_records
        }

    @http.route('/api/v1/employee/profile', type='json', auth='none', methods=['POST', 'GET'], csrf=False)
    def employee_profile(self, **kwargs):
        """
        Retrieves basic details about an employee based on user ID or barcode query.
        """
        if not self._validate_token():
            return {
                'status': 'error',
                'message': 'Unauthorized.'
            }

        pin = kwargs.get('employee_pin')
        if not pin:
            return {
                'status': 'error',
                'message': 'employee_pin is required.'
            }

        employee = request.env['hr.employee'].sudo().search([
            '|', ('barcode', '=', pin), ('pin', '=', pin)
        ], limit=1)

        if not employee:
            return {
                'status': 'error',
                'message': 'Employee not found.'
            }

        return {
            'status': 'success',
            'employee': {
                'id': employee.id,
                'name': employee.name,
                'pin': employee.pin or employee.barcode,
                'job_title': employee.job_title,
                'department': employee.department_id.name,
                'company': employee.company_id.name,
            }
        }
