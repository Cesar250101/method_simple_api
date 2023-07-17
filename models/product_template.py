# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountInvoice(models.Model):
    _inherit = 'product.template'

    para_liquidacion = fields.Boolean(string='Liquidación Factura?')
