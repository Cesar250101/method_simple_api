# -*- coding: utf-8 -*-

import base64
from odoo import models, fields, api
from http.client import HTTPSConnection
from base64 import b64encode
import requests, os,json
import shutil
import codecs
import pdf417gen
import xml.etree.ElementTree as ET
from odoo.exceptions import UserError

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    sii_track_id = fields.Integer('ID Envío')

    @api.multi
    def invoice_validate(self):
        factura=self._generar_xml()
        if self.document_class_id.sii_code not in(46,110):
            return super(AccountInvoice, self).invoice_validate()        



    @api.model
    def _certificar(self,compañia):
        files = [
                ('files', (compañia.simple_api_nombre_certificado, open(compañia.simple_api_ruta_certificado+'\\'+compañia.simple_api_nombre_certificado, 'rb'), 'application/x-pkcs12')),
            ]            

        return files        

    @api.one
    def _obtener_acteco(self):
        compañia=self.env.user.company_id
        codigos=[]
        for c in compañia.company_activities_ids:
            codigos.append(c.code)
        return codigos

    @api.one
    def _obtener_lineas(self):
        detalle={}
        for l in self.invoice_line_ids:
            for t in l.invoice_line_tax_ids:
                indicador_exento=1 if t.amount == 0 else 0
                detalle={
                    "IndicadorExento": indicador_exento,
                    "Nombre": l.product_id.product_tmpl_id.name,
                    "Descripcion": l.name,
                    "Cantidad": int(l.quantity),
                    "UnidadMedida": l.uom_id.name,
                    "Precio": int(l.price_unit),
                    "Descuento": int(l.discount),
                    "Recargo": 0,
                    "MontoItem": int(l.price_subtotal)
                }
                detalle.update(detalle);

        return detalle

    @api.model
    def _obtener_DR(self):
        if self.global_descuentos_recargos:
            drs={}
            for l in self.global_descuentos_recargos:
                tipo='descuento' if l.type=='D' else 'recargo'
                dr={
                    "TipoMovimiento":tipo,
                    "Descripcion": l.gdr_detail,
                    "TipoValor": "Pesos",
                    "Valor": int(self.amount_untaxed_global_discount)
                }
                drs.update(dr)

            return drs
        else:
            return None

    @api.model
    def _obtener_referencias(self):
        if self.referencias:
            referencias={}
            for l in self.referencias:
                referencia={
                    "FechaDocumentoReferencia": l.fecha_documento,
                    "TipoDocumento": l.sii_referencia_TpoDocRef,
                    "CodigoReferencia": l.sii_referencia_CodRef,
                    "RazonReferencia": l.motivo,
                    "FolioReferencia": l.origen
                }
                referencias.update(referencia)

            return referencias
        else:
            return None


    @api.one
    def _generar_xml(self):
        if self.document_class_id.sii_code in(46,110):
            compañia=self.env.user.company_id
            ruta_certificado=compañia.simple_api_ruta_certificado
    #Obtiene folios desde la clase de documentos        
            journal_document_class_id=self.env['account.journal.sii_document_class'].search([('sii_document_class_id','=',self.document_class_id.id)])         
            domain=[('sii_code','=',self.document_class_id.sii_code),
            ('journal_id','=',self.journal_id.id),
            ('sii_document_number','!=',False)
            ]
            folio=self.env['account.invoice'].search(domain,order="sii_document_number desc", limit=1).sii_document_number
            folio+=1
            codigos_actividad=[]
            for a in self._obtener_acteco():
                codigos_actividad.append(a[0])

            if self.use_documents and self.journal_id.type=='purchase': 
                url = compañia.simple_api_servidor+"/api/v1/dte/generar"
                payload={
                "Documento": {
                    "Encabezado": {
                        "IdentificacionDTE": {
                            "TipoDTE": self.document_class_id.sii_code,
                            "Folio":folio,
                            "FechaEmision": self.date_invoice.isoformat(),
                            "FechaVencimiento": self.date_due.isoformat(),
                            "FormaPago": 2
                        },
                        "Emisor": {
                            "Rut": compañia.partner_id.document_number.replace('.',''),
                            "RazonSocial": compañia.partner_id.name,
                            "Giro": compañia.partner_id.activity_description.name,
                            "ActividadEconomica": codigos_actividad,
                            "DireccionOrigen": compañia.partner_id.street,
                            "ComunaOrigen": compañia.partner_id.city_id.name,
                            "Telefono": [compañia.partner_id.phone if compañia.partner_id.phone else None,compañia.partner_id.mobile if compañia.partner_id.mobile else None]
                        },
                        "Receptor": {
                            "Rut": self.partner_id.document_number,
                            "RazonSocial": self.partner_id.name,
                            "Direccion": self.partner_id.street,
                            "Comuna": self.partner_id.city_id.name,
                            "Giro": self.partner_id.activity_description.name,
                            "Contacto": self.partner_id.mobile if self.partner_id.mobile else None
                        },
                        "RutSolicitante": "",
                        "Transporte": None,
                        "Totales": {
                            "MontoNeto": int(self.amount_untaxed),
                            "TasaIVA": 19,
                            "IVA": int(self.amount_tax),
                            "MontoTotal": int(self.amount_total)
                        }
                    },
                    "Detalles":self._obtener_lineas(),
                
                },

                # payload["Certificado"]=self._get_certificado(compañia)

                # "Certificado": {
                #     "Rut": compañia.simple_api_rut_certificado,
                #     "Password": compañia.simple_api_password_certificado
                #                 }
                }
                payload["Certificado"]=self._get_certificado(compañia)            
    #Agrega las referencias del documento            
                if self.referencias:
                    payload["Referencias"]=self._obtener_referencias()
                if self.global_descuentos_recargos:
                    payload["DescuentosRecargos"]=self._obtener_DR()
                json_payload=json.dumps(payload)

    #Firma y timbre el XML            
                files=self._firmar_Timbrar_xml(payload,compañia)            
                response = self.generar_xml_dte(files,folio)
                sobre=self.generar_sobre_envio(response[1],compañia,folio,receptor='60803000-K')
                envio=self.enviar_sobre_envio(sobre[1],compañia,tipo=1)
            elif self.document_class_id.sii_code==110:
                payload={
                "Exportaciones":{
                    "Encabezado":{
                        "IdentificacionDTE":{
                            "TipoDTE":self.document_class_id.sii_code,
                            "Folio":folio,
                            "FechaEmision":self.date_invoice.isoformat(),
                            "FechaVencimiento":self.date_due.isoformat(),
                            "FormaPago":self.payment_term_id.dte_sii_code,
                            "FormaPagoExportacion":self.payment_term_id.forma_pago_aduanas.code,
                            "MedioPago":self.payment_term_id.modalidad_venta.code,
                            "IndServicio":self.ind_servicio
                        },

                        "Emisor": {
                            "Rut": compañia.partner_id.document_number.replace('.',''),
                            "RazonSocial": compañia.partner_id.name,
                            "Giro": compañia.partner_id.activity_description.name,
                            "ActividadEconomica": codigos_actividad,
                            "DireccionOrigen": compañia.partner_id.street,
                            "ComunaOrigen": compañia.partner_id.city_id.name,
                            "Telefono": [compañia.partner_id.phone if compañia.partner_id.phone else None]
                        },

                        "Receptor": {
                            "Rut": '55555555-5',
                            "RazonSocial": self.partner_id.name,
                            "Direccion": self.partner_id.street,
                            "Comuna": self.partner_id.city_id.name,
                            "Giro": self.partner_id.activity_description.name,
                            "Extranjero":{
                            "Nacionalidad":self.partner_id.country_id.vat_label
                            }
                        },

                        "Transporte":{
                            "Aduana":{
                                "CodigoModalidadVenta":self.payment_term_id.modalidad_venta.code
                            }
                        },

                        "Totales":{
                            "TipoMoneda":"DOLAR_ESTADOUNIDENSE",
                            "MontoExento":self.amount_total,
                            "MontoTotal":self.amount_total
                        },
                        "OtraMoneda":{
                            "TipoMoneda":"PESO_CHILENO",
                            "TipoCambio":self.currency_id.inverse_rate,
                            "MontoExento":round(self.amount_total*self.currency_id.inverse_rate,0),
                            "MontoTotal":round(self.amount_total*self.currency_id.inverse_rate,0) 
                        }
                    },
                    "Detalles":self._obtener_lineas(),
                    # "DescuentosRecargos":self._obtener_DR(),
                },
                }
                payload["Certificado"]=self._get_certificado(compañia)      
                files=self._firmar_Timbrar_xml(payload,compañia)            
                response = self.generar_xml_dte(files,folio)
                sobre=self.generar_sobre_envio(response[1],compañia,folio,receptor='60803000-K')
                envio=self.enviar_sobre_envio(sobre[1],compañia,tipo=1)
            dict_text = json.loads(envio.text)  
            print(envio.status_code)          
            if envio.status_code==200:
                self.sii_message=dict_text['responseXml']

                self.sii_result='Enviado'
                self.sii_document_number=folio

                nombre_archivo=self._obtener_nombre_xml(response[1])
                with open(response[1], 'r') as f:
                    dte_envio = f.read()

                if not self.sii_xml_request:
                    envio_id = self.env["sii.xml.envio"].create({
                            'name': nombre_archivo,
                            'xml_envio': dte_envio,
                            'invoice_ids': [[6,0, self.ids]],
                        })      
                self.write({
                    'state':'open'
                })
                tree = ET.parse(response[1])
                root = tree.getroot()
                if self.document_class_id.sii_code!=110:      
                    tag = root.find("Documento")  
                else:
                    tag = root.find("Exportaciones")  

                ted=tag.find("TED")
                tag_string = ET.tostring(ted, encoding='utf8', method='xml')
                self.sii_barcode=tag_string
                self._get_barcode_img()
#Actualiza secuencia
                secuencia=self.env['ir.sequence'].search([('sii_document_class_id','=',self.document_class_id.id)])
                secuencia.write({
                                    'number_next_actual':folio
                                })
            else:
                raise UserError("Ocurrio un error al enviar el documento al SII, la razón es {}".format(dict_text['responseXml']))

    @api.model
    def _get_timbre(self,pathDTE):
        compañia=self.env.user.company_id
        headers = {
                'Authorization': compañia.simple_api_token,
            }        
        url = compañia.simple_api_servidor+"/api/v1/impresion/timbre"
        file=self._get_xml(pathDTE)
        response = requests.post(url, headers=headers, files=file)

        return response.text

    @api.model
    def _get_xml(self,pathDTE):
        posicion=(pathDTE.find('DTE_'))
        nombre=pathDTE[posicion:]
        files = [
                ('files',(nombre,open(pathDTE,'rb'),'text/xml'))
            ]            
        return files

    @api.model
    def _get_certificado(self,compañia):
        certificado={
                    "Rut": compañia.simple_api_rut_certificado,
                    "Password": compañia.simple_api_password_certificado
                }    
        return certificado    

#Genera XML de DTE
    @api.model
    def generar_xml_dte(self,files,folio):
        compañia=self.env.user.company_id
        headers = {
                #'Authorization': 'Basic bWV0aG9kOjIwMTA2MjZBYg==',
                'Authorization': compañia.simple_api_token,
            }        
        url = compañia.simple_api_servidor+"/api/v1/dte/generar"

        response = requests.post(url, headers=headers, files=files)
        pathDTE = os.path.join(compañia.simple_api_ruta_dte,'DTE_'+str(self.document_class_id.sii_code)+'_'+compañia.partner_id.document_number.replace('.','')+'_'+str(folio)+'.xml' )
        with codecs.open(pathDTE,'w+',"ISO-8859-1") as f:            
            f.write(response.text)
            dte=f.read()
        return response.text,pathDTE

#Genera Caratula sobre envío
    @api.model
    def generar_caratula(self,company,receptor='60803000-K' ):
        caratula={
                    "RutEmisor": company.partner_id.document_number.replace('.',''),
                    "RutReceptor": receptor,
                    "FechaResolucion": company.dte_resolution_date.isoformat(),
                    "NumeroResolucion": company.dte_resolution_number
                }
        return caratula

#Genera sobre de envío
    @api.model
    def generar_sobre_envio(self,pathDTE,company,folio,receptor='60803000-K'):  
        url = company.simple_api_servidor+"/api/v1/envio/generar"

        payload={
        "Certificado": self._get_certificado(company),
        "Caratula": self.generar_caratula(company,receptor='60803000-K')
        }
        print(payload)
        files=self._firmar_Timbrar_xml_sobre(payload,company,pathDTE)

        headers = {
                'Authorization': company.simple_api_token,
            }        

        response = requests.post(url, headers=headers, files=files)
        pathDTE = os.path.join(company.simple_api_ruta_dte,'Envio_DTE_'+str(self.document_class_id.sii_code)+'_'+company.partner_id.document_number.replace('.','')+'_'+str(folio)+'.xml' )

        with codecs.open(pathDTE, 'w+', encoding='iso-8859-1') as f:
            f.write(response.text)
        with codecs.open(pathDTE, 'r+', encoding='iso-8859-1') as f:
            dte=f.read()
        self.sii_xml_dte= dte        
        return response,pathDTE

#Envía sobre de envío
    @api.model
    def enviar_sobre_envio(self,pathDTE,company,tipo=0):  
        url = company.simple_api_servidor+"/api/v1/envio/enviar"

        payload={
        "Certificado": self._get_certificado(company),
        "Ambiente":0 if company.dte_service_provider=='SIICERT' else 1,
        "Tipo":tipo
        }

        files=self._firmar_Timbrar_xml_sobre(payload,company,pathDTE)

        headers = {
                'Authorization': company.simple_api_token,
            }        

        response = requests.post(url, headers=headers, files=files)
        return response


    @api.model
    def _obtener_nombre_xml(self,pathDTE):          
        posicion=(pathDTE.find('DTE_'))
        nombre=pathDTE[posicion:]
        return nombre

    @api.model
    def _adjuntar_xml(self,pathDTE):          
        nombre_xml=self._obtener_nombre_xml(pathDTE)
        files=[
        ('files',(nombre_xml,open(pathDTE,'rb'),'text/xml'))
        ]
        return files

    @api.model
    def _firmar_Timbrar_xml_sobre(self,payload,compañia,pathDTE):
        posicion=(pathDTE.find('DTE_'))
        nombre=pathDTE[posicion:]
        files = [
                ('input', ('', json.dumps(payload), 'application/json')),
                ('files', (compañia.simple_api_nombre_certificado, open(compañia.simple_api_ruta_certificado+'/'+compañia.simple_api_nombre_certificado, 'rb'), 'application/x-pkcs12')),
                ('files',(nombre,open(pathDTE,'rb'),'text/xml'))
            ]            
        return files

    @api.model
    def _firmar_Timbrar_xml(self,payload,compañia):
        caf=self.env['dte.caf'].search([('sii_document_class','=',self.document_class_id.sii_code)])
        archivo_caf=caf.obtener_caf()
        print(archivo_caf)
        nombre_caf=archivo_caf[0]['name']
        ruta_completa_caf=compañia.simple_api_ruta_caf+nombre_caf
        print(payload)
        files = [
                ('input', ('', json.dumps(payload), 'application/json')),
                ('files', (compañia.simple_api_nombre_certificado, open(compañia.simple_api_ruta_certificado+compañia.simple_api_nombre_certificado, 'rb'), 'application/x-pkcs12')),
                ('files', (nombre_caf, open(ruta_completa_caf, 'rb'), 'text/xml'))
            ]            

        return files