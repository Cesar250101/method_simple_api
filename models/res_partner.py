# -*- coding: utf-8 -*-

from odoo import models, fields, api

class Paises(models.Model):
    _inherit = 'res.partner'

    # codigo_qbli_bool = fields.Boolean(string='Usa código QBLI')