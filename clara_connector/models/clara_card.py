# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging
import json

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
    status = fields.Selection(selection=[
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('pending', 'Pending'),
        ('locked', 'Locked'),
        ('master_locked', 'Master Locked'),
        ('cancelled', 'Cancelled'),
        ('clara_blocked', 'Clara Blocked'),
        ('closed', 'Closed')
    ], string="Status", default='active', tracking=True, help="Card operational status")
    credit_limit = fields.Monetary("Credit Limit", currency_field='currency_id')
    threshold = fields.Monetary("Threshold", currency_field='currency_id')
    periodicity = fields.Selection([
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('ANNUAL', 'Annual'),
        ('LIFETIME', 'Lifetime'),
        ('SINGLE_USE', 'Single Use'),
    ], string="Periodicity")
    currency_id = fields.Many2one('res.currency')
    cardholder_name = fields.Char("Cardholder Name")
    cardholder_uuid = fields.Char("Cardholder UUID")
    employee_id = fields.Many2one('hr.employee', string="Employee")
    last_sync_date = fields.Datetime("Last Sync")
    raw_payload = fields.Text("Raw Payload")

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
                    uuid_val = (
                        item.get('uuid') or 
                        item.get('id') or 
                        item.get('card_id') or 
                        item.get('card_uuid') or 
                        item.get('clara_id') or
                        item.get('clara_uuid')
                    )
                    if not uuid_val: 
                        _logger.warning("Skipping Clara Card: No ID found in payload %s", item)
                        continue
                    
                    def safe_float(v):
                        try:
                            if isinstance(v, (int, float)): return float(v)
                            return float(v or 0.0)
                        except (ValueError, TypeError):
                            return 0.0

                    # Financial Fields
                    threshold_amt = safe_float(item.get('threshold'))
                    credit_limit_amt = safe_float(item.get('creditLimitValue') or item.get('creditLimit') or threshold_amt)
                    
                    # Currency
                    currency_code = item.get('currency', 'MXN')
                    currency = self.env['res.currency'].search([('name', '=', currency_code)], limit=1)
                    if not currency: currency = self.env.company.currency_id

                    # Cardholder
                    user = item.get('user') or item.get('holder') or item.get('cardholder') or {}
                    user_name = user.get('name') or user.get('fullName') or item.get('holderName', '')
                    
                    # Status
                    status_raw = str(item.get('status', 'active')).lower()
                    allowed_statuses = [s[0] for s in self._fields['status'].selection]
                    if status_raw not in allowed_statuses:
                        status_raw = 'active'

                    # Type
                    type_raw = str(item.get('type') or item.get('cardType') or 'PHYSICAL').upper()
                    type_map = {'PHYSICAL': '1', 'VIRTUAL': '2', 'SINGLE_USE': '3'}

                    # Periodicity
                    periodicity_raw = str(item.get('periodicity') or 'MONTHLY').upper()

                    vals = {
                        'clara_uuid': uuid_val,
                        'alias': item.get('alias') or item.get('name') or 'Clara Card',
                        'last_four': item.get('lastFour') or item.get('last4') or '',
                        'card_type': type_map.get(type_raw, '1'),
                        'status': status_raw,
                        'credit_limit': credit_limit_amt,
                        'threshold': threshold_amt,
                        'periodicity': periodicity_raw,
                        'currency_id': currency.id,
                        'cardholder_name': user_name,
                        'cardholder_uuid': user.get('id', user.get('uuid', '')),
                        'raw_payload': json.dumps(item, indent=2, default=str),
                        'last_sync_date': fields.Datetime.now()
                    }
                    
                    # Match employee by name
                    emp = self.env['hr.employee'].search([('name', 'ilike', user_name)], limit=1) if user_name else False
                    vals['employee_id'] = emp.id if emp else False
                    
                    try:
                        with self.env.cr.savepoint():
                            existing = self.search([('clara_uuid', '=', uuid_val)], limit=1)
                            if existing:
                                existing.write(vals)
                                updated += 1
                                current_rec = existing
                            else:
                                current_rec = self.create(vals)
                                created += 1
                            current_rec.flush_recordset()
                    except Exception as db_ex:
                        self.env.invalidate_all()
                        raise db_ex

                except Exception as ex:
                    _logger.error("Failed to sync card %s: %s", item.get('uuid', 'N/A'), str(ex))
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
