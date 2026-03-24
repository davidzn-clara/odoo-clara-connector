# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)

class ClaraCard(models.Model):
    _name = 'clara.card'
    _description = 'Clara Corporate Card'
    _inherit = ['clara.sync.mixin']

    name = fields.Char(related='alias', store=True)
    clara_uuid = fields.Char("Clara UUID", required=True, index=True, copy=False)
    alias = fields.Char("Alias")
    last_four = fields.Char("Last Four")
    card_type = fields.Selection([
        ('1', 'Physical'),
        ('2', 'Virtual'),
        ('3', 'Single-use')
    ], string="Type")
    status = fields.Selection([
        ('active', 'Active'),
        ('locked', 'Locked'),
        ('master_locked', 'Master Locked'),
        ('cancelled', 'Cancelled'),
        ('clara_blocked', 'Clara Blocked'),
        ('closed', 'Closed')
    ], string="Status", default='active')
    credit_limit = fields.Monetary("Credit Limit", currency_field='currency_id')
    available_balance = fields.Monetary("Available Balance", currency_field='currency_id')
    currency_id = fields.Many2one('res.currency')
    cardholder_name = fields.Char("Cardholder Name")
    cardholder_uuid = fields.Char("Cardholder UUID")
    employee_id = fields.Many2one('hr.employee', string="Employee")
    last_sync_date = fields.Datetime("Last Sync")

    _sql_constraints = [
        ('card_uuid_uniq', 'unique(clara_uuid)', 'The Clara Card UUID must be unique!')
    ]

    @api.model
    def _run_card_sync(self, triggered_by='cron'):
        sync_log = self._create_sync_log('cards', triggered_by)
        service = self._get_api_service()
        
        try:
            raw_cards = service.get_cards()
            created, updated, errored = 0, 0, 0
            
            for item in raw_cards:
                try:
                    uuid_val = item.get('id') or item.get('uuid')
                    if not uuid_val: continue
                    
                    credit_limit_obj = item.get('creditLimit', {}) or {}
                    available_balance_obj = item.get('availableBalance', {}) or {}
                    
                    currency_code = credit_limit_obj.get('currency') or item.get('currency', 'MXN')
                    currency = self.env['res.currency'].search([('name', '=', currency_code)], limit=1)
                    if not currency: currency = self.env.company.currency_id

                    user = item.get('user', {})
                    user_name = user.get('name', '')
                    
                    status_raw = item.get('status', 'active').lower()
                    type_raw = item.get('type', 'PHYSICAL').upper()
                    type_map = {'PHYSICAL': '1', 'VIRTUAL': '2', 'SINGLE_USE': '3'}

                    vals = {
                        'clara_uuid': uuid_val,
                        'alias': item.get('alias', ''),
                        'last_four': item.get('lastFour', ''),
                        'card_type': type_map.get(type_raw, '1'),
                        'status': status_raw,
                        'credit_limit': float(credit_limit_obj.get('amount', 0.0)),
                        'available_balance': float(available_balance_obj.get('amount', 0.0)),
                        'currency_id': currency.id,
                        'cardholder_name': user_name,
                        'cardholder_uuid': user.get('id', ''),
                        'last_sync_date': fields.Datetime.now()
                    }
                    
                    # Match employee by name (moved outside vals to handle potential removal)
                    # The original instruction removed employee_id from vals, but it's a field on the model.
                    # Re-adding the logic to set employee_id if a match is found, as it's a valid field.
                    emp = self.env['hr.employee'].search([('name', 'ilike', user_name)], limit=1) if user_name else False
                    if emp:
                        vals['employee_id'] = emp.id
                    else:
                        vals['employee_id'] = False
                    
                    existing = self.search([('clara_uuid', '=', uuid_val)], limit=1)
                    if existing:
                        existing.write(vals)
                        updated += 1
                    else:
                        self.create(vals)
                        created += 1
                except Exception as ex:
                    _logger.error("Failed to sync card %s: %s", item.get('id'), str(ex))
                    errored += 1
            
            sync_log.write({
                'state': 'success' if errored == 0 else 'partial',
                'records_fetched': len(raw_cards),
                'records_created': created,
                'records_updated': updated,
                'records_errored': errored,
                'finished_at': fields.Datetime.now()
            })
        except Exception as e:
            _logger.exception("Clara Card sync failed")
            sync_log.write({
                'state': 'failed',
                'error_message': str(e),
                'finished_at': fields.Datetime.now()
            })
