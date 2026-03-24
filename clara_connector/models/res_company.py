# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResCompany(models.Model):
    _inherit = 'res.company'

    clara_country = fields.Selection([
        ('mx', 'Mexico'),
        ('co', 'Colombia'),
        ('br', 'Brazil')
    ], string="Clara Country", default='mx')
    clara_client_id = fields.Char("Clara Client ID")
    clara_client_secret = fields.Char("Clara Client Secret")
    clara_tax_identifier = fields.Char("Company Tax ID (RFC/NIT/CNPJ)")

    clara_ca_cert = fields.Binary(string="CA Certificate (.pem)", attachment=True)
    clara_client_cert = fields.Binary(string="Client Certificate (.crt)", attachment=True)
    clara_client_key = fields.Binary(string="Client Private Key (.key)", attachment=True)
    clara_cert_uploaded_date = fields.Datetime("Certificates Uploaded On", readonly=True)

    @api.onchange('clara_ca_cert', 'clara_client_cert', 'clara_client_key')
    def _onchange_clara_certs(self):
        if any([self.clara_ca_cert, self.clara_client_cert, self.clara_client_key]):
            self.clara_cert_uploaded_date = fields.Datetime.now()
