# -*- coding: utf-8 -*-

from odoo import models, fields, api
from http.client import HTTPSConnection
from base64 import b64encode
from datetime import date



class Company(models.Model):
    _inherit = 'dte.caf'

    @api.one
    def obtener_caf(self,folio=0):
        next_number=folio
        today = str(date.today())
        domain=[
            ('sii_document_class','=',self.sii_document_class),
            ('expiration_date','>=',today),
            ('start_nm','<=',next_number),
            ('final_nm','>=',next_number)
        ]
        archivo_caf=self.search(domain,order="expiration_date")
        return archivo_caf
