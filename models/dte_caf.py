# -*- coding: utf-8 -*-

from odoo import models, fields, api
from http.client import HTTPSConnection
from base64 import b64encode
from datetime import date



class Company(models.Model):
    _inherit = 'dte.caf'

    @api.one
    def obtener_caf(self):
        next_number=self.sequence_id.next_by_id()
        today = str(date.today())
        domain=[
            ('sii_document_class','=',self.sii_document_class),
            ('expiration_date','>=',today),
            ('start_nm','<=',next_number),
            ('final_nm','>=',next_number)
        ]
        archivo_caf=self.search(domain,order="expiration_date")
        return archivo_caf
