# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging
import json

_logger = logging.getLogger(__name__)

class ClaraInvoice(models.Model):
    _name = 'clara.invoice'
    _description = 'Clara Recovered Invoice (CFDI)'
    _inherit = ['clara.sync.mixin']
    _order = 'date desc, id desc'

    name = fields.Char("Invoice Number", required=True, index=True)
    sat_uuid = fields.Char("SAT UUID", index=True, help="Universal Unique Identifier from the Tax Authority (Mexico)")
    clara_uuid = fields.Char("Clara UUID", required=True, index=True, copy=False)
    
    issuer_rfc = fields.Char("Issuer RFC")
    issuer_name = fields.Char("Issuer Name")
    receiver_rfc = fields.Char("Receiver RFC")
    
    date = fields.Date("Invoice Date")
    amount_total = fields.Monetary("Total Amount", currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string="Currency")
    
    status = fields.Selection([
        ('valid', 'Valid'),
        ('cancelled', 'Cancelled'),
    ], string="Fiscal Status", default='valid')

    transaction_id = fields.Many2one('clara.transaction', string="Related Transaction")
    raw_payload = fields.Text("Raw Payload", groups="base.group_no_one")

    _sql_constraints = [
        ('clara_uuid_uniq', 'unique(clara_uuid)', 'The Clara Invoice UUID must be unique!')
    ]

    @api.model
    def _run_invoice_sync(self, triggered_by='cron', from_date=None, to_date=None):
        sync_log = self._create_sync_log('invoices', triggered_by)
        service = self._get_api_service()
        
        try:
            raw_invoices = service.get_invoices(from_date=from_date, to_date=to_date)
            created, updated, errored = 0, 0, 0
            
            for item in raw_invoices:
                try:
                    uuid_val = (
                        item.get('uuid') or 
                        item.get('id') or 
                        item.get('invoice_uuid') or 
                        item.get('clara_id')
                    )
                    if not uuid_val: continue
                    
                    currency_code = item.get('currency', 'MXN')
                    currency = self.env['res.currency'].search([('name', '=', currency_code)], limit=1)
                    if not currency: currency = self.env.company.currency_id

                    vals = {
                        'clara_uuid': uuid_val,
                        'name': item.get('invoiceNumber') or item.get('folio') or item.get('name') or 'INV-TEMP',
                        'sat_uuid': item.get('satUuid') or item.get('uuidSat'),
                        'issuer_rfc': item.get('issuerRfc') or item.get('emitterRfc') or item.get('rfc'),
                        'issuer_name': item.get('issuerName') or item.get('emitterName') or item.get('vendorName'),
                        'receiver_rfc': item.get('receiverRfc'),
                        'date': item.get('date') or item.get('issueDate') or item.get('createdAt'),
                        'amount_total': float(item.get('total') or item.get('amount') or 0.0),
                        'currency_id': currency.id,
                        'status': 'valid' if str(item.get('status', 'valid')).lower() != 'cancelled' else 'cancelled',
                        'raw_payload': json.dumps(item, indent=2, default=str),
                    }
                    
                    # Try to link to transaction
                    tx_uuid = item.get('transactionUuid') or item.get('transactionId')
                    if tx_uuid:
                        tx = self.env['clara.transaction'].search([('clara_uuid', '=', tx_uuid)], limit=1)
                        if tx:
                            vals['transaction_id'] = tx.id

                    with self.env.cr.savepoint():
                        existing = self.search([('clara_uuid', '=', uuid_val)], limit=1)
                        if existing:
                            existing.write(vals)
                            updated += 1
                        else:
                            self.create(vals)
                            created += 1
                            
                except Exception as ex:
                    _logger.error("Failed to sync invoice %s: %s", item.get('uuid', 'N/A'), str(ex))
                    errored += 1
            
            sync_log.write({
                'state': 'success' if errored == 0 else 'partial',
                'records_fetched': len(raw_invoices),
                'records_created': created,
                'records_updated': updated,
                'records_errored': errored,
                'finished_at': fields.Datetime.now()
            })
        except Exception as e:
            _logger.exception("Clara Invoice sync failed")
            sync_log.write({
                'state': 'failed',
                'error_message': str(e),
                'finished_at': fields.Datetime.now()
            })
