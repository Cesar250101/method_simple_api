# -*- coding: utf-8 -*-

import json
import requests
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

class APICAFDocs(models.TransientModel):
    _inherit = "dte.caf.apicaf.docs"


class APICAF(models.TransientModel):
    _inherit = "dte.caf.apicaf"


    @api.onchange('company_id')
    def get_caf(self):
        compañia=self.env.user.company_id
        headers = {
                #'Authorization': 'Basic bWV0aG9kOjIwMTA2MjZBYg==',
                'Authorization': compañia.simple_api_token,
            }        
        url = compañia.simple_api_servidor+':5000'+"/api/folios/get/"+str(self.cod_docto.sii_code)
        file=compañia._certificar(compañia)
        datos={
                            "RutCertificado":compañia.simple_api_rut_certificado,
                            "Password":compañia.simple_api_password_certificado,
                            "RutEmpresa":compañia.partner_id.document_number.replace('.',''),
                            "Ambiente":0 if compañia.dte_service_provider=='SIICERT' else 1           
            
                }
        payload={
                "input":str(datos) }
        
        json_payload=json.dumps(payload)
        print(json_payload)
        json_payload=json.loads(json_payload)
        print(json_payload)
        response = requests.request("GET", url, headers=headers, data=json_payload, files=file)        
        if response.status_code==200:
            self.cant_doctos=response.text

