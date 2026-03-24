# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ..services.clara_api_service import ClaraAPIService
import logging

_logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    clara_country = fields.Selection(related='company_id.clara_country', readonly=False)
    clara_client_id = fields.Char(related='company_id.clara_client_id', readonly=False)
    clara_client_secret = fields.Char(related='company_id.clara_client_secret', readonly=False)
    clara_tax_identifier = fields.Char(related='company_id.clara_tax_identifier', readonly=False)
    
    clara_ca_cert = fields.Binary(related='company_id.clara_ca_cert', readonly=False)
    clara_client_cert = fields.Binary(related='company_id.clara_client_cert', readonly=False)
    clara_client_key = fields.Binary(related='company_id.clara_client_key', readonly=False)
    clara_cert_uploaded_date = fields.Datetime(related='company_id.clara_cert_uploaded_date', readonly=True)

    clara_sync_interval_hours = fields.Integer("Auto-sync frequency (hours)", config_parameter='clara_connector.clara_sync_interval_hours', default=6)
    clara_sync_from_date = fields.Datetime("Sync From Date", config_parameter='clara_connector.clara_sync_from_date')
    clara_auto_create_expenses = fields.Boolean("Auto Create Expenses", config_parameter='clara_connector.clara_auto_create_expenses', default=True)
    clara_auto_post_moves = fields.Boolean("Auto Post Moves", config_parameter='clara_connector.clara_auto_post_moves', default=False)
    clara_request_timeout = fields.Integer("API Timeout (seconds)", config_parameter='clara_connector.clara_request_timeout', default=30)
    
    clara_journal_id = fields.Many2one('account.journal', string="Clara Journal", domain="[('type', 'in', ('bank', 'general'))]", config_parameter='clara_connector.clara_journal_id')
    clara_liability_account_id = fields.Many2one('account.account', string="Clara Liability Account", config_parameter='clara_connector.clara_liability_account_id')
    clara_default_expense_account_id = fields.Many2one('account.account', string="Default Expense Account", config_parameter='clara_connector.clara_default_expense_account_id')
    clara_default_product_id = fields.Many2one('product.product', string="Default Expense Product", config_parameter='clara_connector.clara_default_product_id')
    clara_default_employee_id = fields.Many2one('hr.employee', string="Fallback Employee", config_parameter='clara_connector.clara_default_employee_id')

    @api.onchange('clara_ca_cert', 'clara_client_cert', 'clara_client_key')
    def _onchange_clara_certs(self):
        if any([self.clara_ca_cert, self.clara_client_cert, self.clara_client_key]):
            self.clara_cert_uploaded_date = fields.Datetime.now()
            
    def action_test_clara_connection(self):
        self.ensure_one()
        # Save before testing since tests rely on DB config
        self.execute()
        
        service = ClaraAPIService(self.env)
        try:
            # Test getting the token implicitly tests certificates and client id/secret
            token = service.get_token()
            # Also test the user scope by making a basic request (paginated, just 1 item)
            txn = service.get_transactions(limit=1, max_records=1)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Connection Successful"),
                    'message': _("Successfully connected to Clara API and verified token flow."),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(_("Connection failed: %s") % str(e))
