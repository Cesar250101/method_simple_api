# -*- coding: utf-8 -*-

from odoo import models, fields, api
from http.client import HTTPSConnection
from base64 import b64encode

class Company(models.Model):
    _inherit = 'ir.sequence'

    @api.model
    def get_next_number(self):
        return self.number_next

