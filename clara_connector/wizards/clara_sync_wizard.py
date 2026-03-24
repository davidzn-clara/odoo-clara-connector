# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class ClaraSyncWizard(models.TransientModel):
    _name = 'clara.sync.wizard'
    _description = 'Manual Clara Sync Wizard'

    sync_type = fields.Selection([
        ('transactions', 'Transactions Only'),
        ('cards', 'Cards Only'),
        ('full', 'Full Sync (Transactions & Cards)')
    ], string="Sync Scope", default='full', required=True)

    def action_run_sync(self):
        self.ensure_one()
        
        if self.sync_type in ('transactions', 'full'):
            self.env['clara.transaction']._run_sync(triggered_by='manual')
            
        if self.sync_type in ('cards', 'full'):
            self.env['clara.card']._run_card_sync(triggered_by='manual')

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Sync Completed"),
                'message': _("Clara synchronization finished successfully. Check Sync Logs for details."),
                'type': 'success',
                'sticky': False,
            }
        }
