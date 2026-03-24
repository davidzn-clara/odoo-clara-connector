# -*- coding: utf-8 -*-
from odoo import api, fields, models

class ClaraSyncLog(models.Model):
    _name = 'clara.sync.log'
    _description = 'Clara Synchronization Log'
    _order = 'started_at desc'

    name = fields.Char("Name", default="New", required=True)
    sync_type = fields.Selection([
        ('transactions', 'Transactions'),
        ('cards', 'Cards'),
        ('billing_statements', 'Billing Statements'),
        ('full', 'Full Sync')
    ], string="Sync Type", required=True)
    state = fields.Selection([
        ('running', 'Running'),
        ('success', 'Success'),
        ('partial', 'Partial Failure'),
        ('failed', 'Failed')
    ], string="State", default='running', required=True)
    started_at = fields.Datetime("Started At", default=fields.Datetime.now)
    finished_at = fields.Datetime("Finished At")
    duration = fields.Float("Duration (s)", compute='_compute_duration')
    records_fetched = fields.Integer("Records Fetched", default=0)
    records_created = fields.Integer("Records Created", default=0)
    records_updated = fields.Integer("Records Updated", default=0)
    records_skipped = fields.Integer("Records Skipped", default=0)
    records_errored = fields.Integer("Records Errored", default=0)
    error_message = fields.Text("Error Message")
    triggered_by = fields.Selection([
        ('cron', 'Cron'),
        ('manual', 'Manual'),
        ('api', 'API')
    ], string="Triggered By", default='manual')

    @api.depends('started_at', 'finished_at')
    def _compute_duration(self):
        for log in self:
            if log.started_at and log.finished_at:
                diff = log.finished_at - log.started_at
                log.duration = diff.total_seconds()
            else:
                log.duration = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                sync_type = dict(self._fields['sync_type'].selection).get(vals.get('sync_type'), 'Sync')
                vals['name'] = f"{sync_type} - {fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return super().create(vals_list)
