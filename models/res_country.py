# -*- coding: utf-8 -*-

from odoo import models, fields, api

class Paises(models.Model):
    _inherit = 'res.country'

    code_dte = fields.Char(string='Código País DTE')