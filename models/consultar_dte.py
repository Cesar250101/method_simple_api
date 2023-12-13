# -*- coding: utf-8 -*-
import json

import requests
from odoo import models, fields, api


class CoonsultarEstadoFactura(models.Model):
    _inherit = 'account.invoice'

    
    @api.model
    def consultar_estado(self):
        compañia=self.env.user.company_id
        payload={
        "Certificado": self._get_certificado(compañia),
        }    
        url = compañia.simple_api_servidor+"/api/v1/consulta/envio"
        invoices=self.env['account.invoice'].search([('sii_result','in',['Enviado','EnCola','NoEnviado','Aceptado'])],limit=30)
        for i in invoices:
            if i.journal_id.type=='sale':
                payload["RutEmpresa"]= compañia.partner_id.document_number.replace('.','')
                payload["TrackId"]= i.sii_track_id if i.sii_track_id!=False else i.sii_xml_request.sii_send_ident
                payload["Ambiente"]= 0 if compañia.dte_service_provider=='SIICERT' else 1 
                payload["ServidorBoletaREST"]=True if i.sii_code==39 else False

                files = [
                    ('input', ('', json.dumps(payload), 'application/json')),
                    ('files', (compañia.simple_api_nombre_certificado, open(compañia.simple_api_ruta_certificado+'/'+compañia.simple_api_nombre_certificado, 'rb'), 'application/x-pkcs12')),
                ]   
    #Request        
                headers = {
                    'Authorization': compañia.simple_api_token,
                }        

                response = requests.post(url, headers=headers, files=files)
                if response.status_code==200:
                    datos_diccionario = json.loads(response.text)

        #Actualiza estado del documento
                    if datos_diccionario['estado']=='EPR':
                        i.sii_result='Proceso'
                    elif datos_diccionario['estado'] in['RSC','SOK','RFR','FOK','RCT']:
                        i.sii_result='Rechazado'
                    elif datos_diccionario['estado'] in['CRT']:
                        i.sii_result='Aceptado'
                    elif datos_diccionario['estado'] in['PDR']:
                        i.sii_result='Enviado'
                    if 'responseXml' in datos_diccionario:
                        i.sii_message=datos_diccionario['responseXml']

class CoonsultarEstadoBoleta(models.Model):
    _inherit = 'pos.order'

    
    @api.model
    def consultar_estado_boleta(self):
        compañia=self.env.user.company_id
        _model_invoice=self.env['account.invoice']
        payload={
        "Certificado": _model_invoice._get_certificado(compañia),
        }    
        url = compañia.simple_api_servidor+"/api/v1/consulta/envio"
        invoices=self.env['pos.order'].search([('sii_result','in',['Enviado','EnCola','Aceptado']),
                                                ('sii_xml_request','!=',False)],limit=50)
        for i in invoices:
            payload["RutEmpresa"]= compañia.partner_id.document_number.replace('.','')
            payload["TrackId"]= i.sii_xml_request.sii_send_ident
            payload["Ambiente"]= 0 if compañia.dte_service_provider=='SIICERT' else 1 
            payload["ServidorBoletaREST"]=True if i.sii_code==39 else False

            files = [
                ('input', ('', json.dumps(payload), 'application/json')),
                ('files', (compañia.simple_api_nombre_certificado, open(compañia.simple_api_ruta_certificado+'/'+compañia.simple_api_nombre_certificado, 'rb'), 'application/x-pkcs12')),
            ]   
#Request        
            headers = {
                'Authorization': compañia.simple_api_token,
            }        

            response = requests.post(url, headers=headers, files=files)
            if response.status_code==200:
                datos_diccionario = json.loads(response.text)

    #Actualiza estado del documento
                if datos_diccionario['estado']=='EPR':
                    i.sii_result='Proceso'
                elif datos_diccionario['estado'] in['RSC','SOK','RFR','FOK','RCT']:
                    i.sii_result='Rechazado'
                elif datos_diccionario['estado'] in['CRT']:
                    i.sii_result='Aceptado'
                elif datos_diccionario['estado'] in['PDR']:
                    i.sii_result='Enviado'
                
                # i.sii_message=datos_diccionario['responseXml']
