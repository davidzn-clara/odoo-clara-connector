# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import json

_logger = logging.getLogger(__name__)

class ClaraTransaction(models.Model):
    _name = 'clara.transaction'
    _description = 'Clara Transaction'
    _inherit = ['clara.sync.mixin']
    _order = 'transaction_date desc'

    clara_uuid = fields.Char("Clara UUID", required=True, index=True, copy=False)
    name = fields.Char(string="Name", compute='_compute_name', store=True)
    amount = fields.Monetary("Amount", currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string="Currency")
    merchant_name = fields.Char("Merchant Name")
    merchant_category = fields.Char("Merchant Category")
    merchant_country = fields.Char("Merchant Country")
    card_uuid = fields.Char("Card UUID")
    card_last_four = fields.Char("Card Last Four")
    cardholder_name = fields.Char("Cardholder Name")
    cardholder_email = fields.Char("Cardholder Email")
    transaction_date = fields.Date("Transaction Date")
    posting_date = fields.Date("Posting Date")
    status = fields.Selection(selection=[
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('declined', 'Declined'),
        ('reversed', 'Reversed'),
        ('inactive', 'Inactive'),
        ('blocked', 'Blocked')
    ], string="Status", default='pending', tracking=True, help="Transaction processing status")
    description = fields.Text("Description")
    billing_statement_uuid = fields.Char("Billing Statement UUID")
    expense_id = fields.Many2one('hr.expense', string="Expense Record")
    account_move_id = fields.Many2one('account.move', string="Journal Entry")
    sync_state = fields.Selection([
        ('new', 'New'),
        ('synced', 'Synced'),
        ('error', 'Error')
    ], string="Sync State", default='new')
    invoice_ids = fields.One2many('clara.invoice', 'transaction_id', string="Fiscal Invoices")
    raw_payload = fields.Text("Raw Payload")
    last_sync_date = fields.Datetime("Last Sync Date")

    _sql_constraints = [
        ('clara_uuid_uniq', 'unique(clara_uuid)', 'The Clara UUID must be unique!')
    ]

    @api.depends('merchant_name', 'transaction_date')
    def _compute_name(self):
        for record in self:
            merchant = record.merchant_name or 'Unknown'
            date_str = record.transaction_date.strftime('%Y-%m-%d') if record.transaction_date else 'NoDate'
            record.name = f"TXN-{merchant}-{date_str}"

    def action_create_expense(self):
        for tx in self.filtered(lambda t: not t.expense_id and t.status == 'approved'):
            config = self.env['ir.config_parameter'].sudo()
            product_id = int(config.get_param('clara_connector.clara_default_product_id', 0))
            if not product_id:
                raise UserError(_("Please configure a Default Expense Product in Clara Settings."))
                
            employee = self._find_employee(tx.cardholder_email, tx.cardholder_name)
            
            expense_vals = {
                'name': f"{tx.merchant_name} - {tx.transaction_date}",
                'total_amount': tx.amount,
                'currency_id': tx.currency_id.id,
                'date': tx.transaction_date,
                'product_id': product_id,
                'employee_id': employee.id if employee else False,
                'description': tx.description or tx.merchant_name,
                'state': 'draft',
            }
            expense = self.env['hr.expense'].create(expense_vals)
            tx.expense_id = expense.id
            tx.sync_state = 'synced'

    def action_post_journal_entry(self):
        for tx in self.filtered(lambda t: not t.account_move_id):
            config = self.env['ir.config_parameter'].sudo()
            journal_id = int(config.get_param('clara_connector.clara_journal_id', 0))
            liability_account_id = int(config.get_param('clara_connector.clara_liability_account_id', 0))
            expense_account_id = int(config.get_param('clara_connector.clara_default_expense_account_id', 0))
            
            if not journal_id or not liability_account_id or not expense_account_id:
                raise UserError(_("Please configure Clara Journal and Accounts in Settings."))
                
            move_vals = {
                'journal_id': journal_id,
                'date': tx.transaction_date,
                'ref': f"Clara TXN {tx.clara_uuid}",
                'move_type': 'entry',
                'line_ids': [
                    (0, 0, {
                        'account_id': expense_account_id,
                        'name': tx.merchant_name,
                        'debit': tx.amount,
                        'credit': 0.0,
                    }),
                    (0, 0, {
                        'account_id': liability_account_id,
                        'name': "Clara Credit Line",
                        'debit': 0.0,
                        'credit': tx.amount,
                    }),
                ]
            }
            move = self.env['account.move'].create(move_vals)
            tx.account_move_id = move.id
            
            if config.get_param('clara_connector.clara_auto_post_moves', 'False') == 'True':
                move.action_post()

    def _find_employee(self, email, name):
        if email:
            emp = self.env['hr.employee'].search([('work_email', '=', email)], limit=1)
            if emp: return emp
        if name:
            emp = self.env['hr.employee'].search([('name', 'ilike', name)], limit=1)
            if emp: return emp
            
        fallback_id = int(self.env['ir.config_parameter'].sudo().get_param('clara_connector.clara_default_employee_id', 0))
        if fallback_id:
            return self.env['hr.employee'].browse(fallback_id)
        return self.env['hr.employee']

    def action_open_expense(self):
        self.ensure_one()
        if self.expense_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'hr.expense',
                'res_id': self.expense_id.id,
                'view_mode': 'form',
            }

    def action_open_move(self):
        self.ensure_one()
        if self.account_move_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': self.account_move_id.id,
                'view_mode': 'form',
            }

    @api.model
    def _run_sync(self, triggered_by='cron'):
        sync_log = self._create_sync_log('transactions', triggered_by)
        config = self.env['ir.config_parameter'].sudo()
        from_date_str = config.get_param('clara_connector.clara_sync_from_date')
        from_date = fields.Date.from_string(from_date_str) if from_date_str else None
        
        service = self._get_api_service()
        try:
            raw_txs = service.get_transactions(from_date=from_date)
            created, updated, errored = 0, 0, 0
            
            auto_expense = config.get_param('clara_connector.clara_auto_create_expenses', 'True') == 'True'
            
            for item in raw_txs:
                try:
                    uuid_val = item.get('id') or item.get('uuid')
                    if not uuid_val:
                        continue
                        
                    merchant = item.get('merchant', {}) or {}
                    user = item.get('user', {}) or {}
                    card = item.get('card', {}) or {}
                    audit = item.get('audit', {}) or {}
                    
                    amount_val = item.get('amountValue', {}) or {}
                    if not amount_val and item.get('amount'):
                        # Compatibility for older or different response shapes
                        amount_val = {'amount': item.get('amount'), 'currency': item.get('currency')}
                    
                    currency_code = amount_val.get('currency') or item.get('currency') or 'MXN'
                    currency = self.env['res.currency'].search([('name', '=', currency_code)], limit=1)
                    if not currency:
                        currency = self.env.company.currency_id
                        
                    # Extract date from audit or standard field
                    txn_date_raw = audit.get('operationDate') or item.get('createdAt') or item.get('transactionDate')
                    txn_date = txn_date_raw.split('T')[0] if txn_date_raw else fields.Date.today()
                    
                    posting_date_raw = audit.get('accountingDate') or item.get('postingDate')
                    posting_date = posting_date_raw.split('T')[0] if posting_date_raw else False

                    vals = {
                        'clara_uuid': uuid_val,
                        'amount': abs(float(amount_val.get('amount', 0.0))), # Use absolute value for Odoo
                        'currency_id': currency.id,
                        'merchant_name': merchant.get('name') or item.get('transactionLabel') or 'Unknown',
                        'merchant_category': merchant.get('category') or merchant.get('description', ''),
                        'merchant_country': merchant.get('country', ''),
                        'card_uuid': card.get('id', card.get('uuid', '')),
                        'card_last_four': card.get('lastFour') or (card.get('maskedPan', '')[-4:] if card.get('maskedPan') else ''),
                        'cardholder_name': user.get('holderName') or user.get('name', ''),
                        'cardholder_email': user.get('email') or user.get('emailAddress', ''),
                        'transaction_date': txn_date,
                        'posting_date': posting_date,
                        'status': item.get('status', 'pending').lower(),
                        'description': item.get('description') or item.get('transactionLabel', ''),
                        'billing_statement_uuid': item.get('billingStatement', {}).get('uuid', '') if isinstance(item.get('billingStatement'), dict) else '',
                        'raw_payload': json.dumps(item, indent=2),
                        'last_sync_date': fields.Datetime.now()
                    }
                    
                    # Use a savepoint to prevent one failure from aborting the whole transaction
                    try:
                        with self.env.cr.savepoint():
                            existing = self.search([('clara_uuid', '=', uuid_val)], limit=1)
                            if existing:
                                existing.write(vals)
                                updated += 1
                                tx = existing
                            else:
                                tx = self.create(vals)
                                created += 1
                                
                            if tx.status == 'approved' and auto_expense and not tx.expense_id:
                                tx.action_create_expense()
                                
                            if not tx.account_move_id and config.get_param('clara_connector.clara_auto_post_moves', 'False') == 'True':
                                tx.action_post_journal_entry()
                            
                            # Force a flush inside the savepoint to catch any SQL errors here
                            tx.flush_recordset()
                    except Exception as db_ex:
                        # Invalidate cache for this record to prevent Odoo from trying to flush it again later
                        self.env.invalidate_all()
                        raise db_ex
                            
                except Exception as ex:
                    _logger.error("Failed to sync transaction %s: %s", item.get('id'), str(ex))
                    errored += 1
            
            sync_log.write({
                'state': 'success' if errored == 0 else 'partial',
                'records_fetched': len(raw_txs),
                'records_created': created,
                'records_updated': updated,
                'records_errored': errored,
                'finished_at': fields.Datetime.now()
            })
            if (created + updated) > 0:
                config.set_param('clara_connector.clara_sync_from_date', fields.Date.today().strftime('%Y-%m-%d'))
            
        except Exception as e:
            _logger.exception("Clara Transaction sync failed")
            sync_log.write({
                'state': 'failed',
                'error_message': str(e),
                'finished_at': fields.Datetime.now()
            })
