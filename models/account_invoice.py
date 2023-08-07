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
from datetime import datetime
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
from odoo.tools.float_utils import float_compare

class AccountInvoice(models.Model):
    _inherit = 'account.invoice.line'

    tiene_code_qbli = fields.Boolean(string='Agregar QBLI?',related='invoice_id.tiene_code_qbli')
    code_qbli = fields.Char(string='Código QBLI')


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    sii_track_id = fields.Char('ID Envío')
    pais_id = fields.Many2one(comodel_name='res.country', string='País')
    tiene_code_qbli = fields.Boolean(string='Agregar QBLI?')
    calculo_liq_auto = fields.Boolean(string='Calculo Automátivo Comisión?')
    fecha_inicial_liq = fields.Datetime(string='Fecha Inicial')
    fecha_final_liq = fields.Datetime(string='Fecha Final')
    marca_id = fields.Many2one(comodel_name='method_minori.marcas', string='Marca')
    neto_marca = fields.Integer(compute='_compute_totales_marca', string='Neto Marca')
    iva_marca = fields.Integer(compute='_compute_totales_marca', string='Iva Marca')
    total_marca = fields.Integer(compute='_compute_totales_marca', string='Total Marca')
    porc_comision = fields.Float(string='% Comisión')
    fijo_comision=fields.Integer(string='Valor Fijo')    
    subtotal_comision=fields.Integer(string='SubTotal Comisión')    
    neto_comision=fields.Integer(string='Neto Comisión',compute='_compute_comision',)    
    iva_comision=fields.Integer(string='Iva Comisión',compute='_compute_comision')
    total_comision=fields.Integer(string='Total Comisión',compute='_compute_comision')
#Manual
    neto_marca_manual = fields.Integer(string='Neto Marca')
    iva_marca_manual = fields.Integer(compute='_compute_neto_marca_manual', string='Iva Marca')
    total_marca_manual = fields.Integer(compute='_compute_neto_marca_manual', string='Total Marca')

    @api.onchange('calculo_liq_auto')
    def _onchange_calculo_liq_auto(self):
        self.marca_id=False
        self.neto_marca=False
        self.iva_marca=False
        self.total_marca=False
        self.neto_marca_manual=False
        self.iva_marca_manual=False
        self.total_marca_manual=False
        self.porc_comision=False
        self.fijo_comision=False
        self.subtotal_comision=False
        self.neto_comision=False
        self.iva_comision=False
        self.total_comision=False
    
    @api.depends('neto_marca_manual')
    def _compute_neto_marca_manual(self):
        if self.calculo_liq_auto==False:
            neto=self.neto_marca_manual
            self.iva_marca_manual=round(neto*0.19)
            self.total_marca_manual=neto+self.iva_marca_manual
    
    @api.onchange('porc_comision','neto_marca','neto_marca_manual','marca_id','fecha_inicial_liq','fecha_final_liq','calculo_liq_auto','fijo_comision')
    def _onchange_comision(self):
        if self.porc_comision:
            valor_neto_marca=self.neto_marca if self.calculo_liq_auto else self.neto_marca_manual            
            subtotal_comision=round(((valor_neto_marca)*(self.porc_comision/100)),0)
            neto_comision=round((subtotal_comision+self.fijo_comision),0)
            iva_comision=round(neto_comision*0.19,0)
            total_comision=neto_comision+iva_comision

            self.subtotal_comision=subtotal_comision
            self.neto_comision=neto_comision
            self.iva_comision=iva_comision
            self.total_comision=total_comision

    @api.depends('porc_comision')
    def _compute_comision(self):
        if self.porc_comision:
            valor_porc_comisión=self.neto_marca if self.calculo_liq_auto else self.neto_marca_manual            
            subtotal_comision=round(((valor_porc_comisión)*(self.porc_comision/100)),0)
            neto_comision=round(subtotal_comision+self.fijo_comision ,0)
            iva_comision=round(neto_comision*0.19,0)
            total_comision=(neto_comision+iva_comision)

            self.subtotal_comision=subtotal_comision
            self.neto_comision=neto_comision
            self.iva_comision=iva_comision
            self.total_comision=total_comision


    @api.one
    def agregar_linea_liquidación(self):
        product_tmpl_id=self.env['product.template'].search([('para_liquidacion','=',True)],limit=1)        
        if product_tmpl_id:
            invoice_line=self.env['account.invoice.line']
            product_id=self.env['product.product'].search([('product_tmpl_id','=',product_tmpl_id.id)],limit=1)        
            vals={
                'product_id':product_id.id,
                'name':product_tmpl_id.name,
                'account_id':product_tmpl_id.categ_id.property_account_expense_categ_id.id,
                'quantity':1,
                'uom_id':product_tmpl_id.uom_po_id.id,
                'price_unit':self.total_marca if self.calculo_liq_auto else self.total_marca_manual,
                'invoice_line_tax_ids':[(6, 0, [product_tmpl_id.taxes_id.id])]             ,                    
                'invoice_id':self.id,
            }
            linea=invoice_line.create(vals)
            linea._get_price_tax()
            if any(line.invoice_line_tax_ids for line in self.invoice_line_ids) and not self.tax_line_ids:
                self.compute_taxes()

            values={
                'amount_untaxed':self.neto_marca if self.calculo_liq_auto else self.neto_marca_manual,
                'amount_tax':self.iva_marca+self.iva_marca_manual,
                'amount_total':self.total_marca if self.calculo_liq_auto else self.total_marca_manual,
                'residual':(self.total_marca if self.calculo_liq_auto else self.total_marca_manual)-self.total_comision,
                'residual_signed':(self.total_marca if self.calculo_liq_auto else self.total_marca_manual)-self.total_comision,
                'residual_company_signed':(self.total_marca if self.calculo_liq_auto else self.total_marca_manual)-self.total_comision,

            }
            self.write(values)
            self._compute_amount()    
            self._compute_sign_taxes()        

        else:
            raise Warning("No ha definido un producto para liquidar facturas, vaya al productos y marque la opción!")            



    @api.depends('fecha_inicial_liq','fecha_final_liq','marca_id')
    def _compute_totales_marca(self):
        if self.calculo_liq_auto:
            if self.fecha_final_liq and self.fecha_inicial_liq and self.marca_id:
                query="""
                            SELECT 
                            sum(pol.price_subtotal)
                            from pos_order po left join sii_document_class sdc on po.document_class_id =sdc.id
                            inner join pos_order_line pol on po.id =pol.order_id 
                            inner join product_product pp on pol.product_id =pp.id
                            inner join product_template pt on pp.product_tmpl_id =pt.id  
                            left join res_partner rp on po.partner_id =rp.id
                            left join method_minori_marcas mmm on pt.marca_id =mmm.id
                            left join product_category pc on pt.categ_id =pc.id 
                            left join pos_session ps on po.session_id =ps.id 
                            left join pos_config pc2 on ps.config_id =pc2.id
                            where date_order between %s and %s
                            and mmm.id =%s
                            union 
                            SELECT 
                            sum(pol.price_subtotal) as neto
                            from account_invoice po left join sii_document_class sdc on po.document_class_id =sdc.id
                            inner join account_invoice_line pol on po.id =pol.invoice_id 
                            inner join product_product pp on pol.product_id =pp.id
                            inner join product_template pt on pp.product_tmpl_id =pt.id  
                            left join res_partner rp on po.partner_id =rp.id
                            left join method_minori_marcas mmm on pt.marca_id =mmm.id
                            left join product_category pc on pt.categ_id =pc.id
                            where po.date_invoice between %s and %s
                            and mmm.id =%s
                        """ 
                self.env.cr.execute(query,[
                                            self.fecha_inicial_liq.strftime("%Y-%m-%d %H:%M:%S"), self.fecha_final_liq.strftime("%Y-%m-%d %H:%M:%S"), self.marca_id.id,
                                            self.fecha_inicial_liq.strftime("%Y-%m-%d %H:%M:%S"), self.fecha_final_liq.strftime("%Y-%m-%d %H:%M:%S"), self.marca_id.id,
                                            ])
                rec=self.env.cr.fetchall()
                neto=0
                for r in rec:
                    if r[0]!=None:
                        neto+=r[0]
                self.neto_marca=neto
                self.iva_marca=round(neto*0.19,0)
                self.total_marca=neto+round(neto*0.19,0)


    @api.multi
    def invoice_validate(self):
        factura=self._generar_xml()
        if self.document_class_id.sii_code not in(46,110,112,43):
            return super(AccountInvoice, self).invoice_validate()        

    @api.multi
    def action_invoice_open(self):
        # lots of duplicate calls to action_invoice_open, so we remove those already open
        to_open_invoices = self.filtered(lambda inv: inv.state != 'open')
        if to_open_invoices.filtered(lambda inv: not inv.partner_id):
            raise UserError(_("The field Vendor is required, please complete it to validate the Vendor Bill."))
        if to_open_invoices.filtered(lambda inv: inv.state != 'draft'):
            raise UserError(_("Invoice must be in draft state in order to validate it."))
        # if to_open_invoices.filtered(lambda inv: float_compare(inv.amount_total, 0.0, precision_rounding=inv.currency_id.rounding) == -1):
        #     raise UserError(_("You cannot validate an invoice with a negative total amount. You should create a credit note instead."))
        if to_open_invoices.filtered(lambda inv: not inv.account_id):
            raise UserError(_('No account was found to create the invoice, be sure you have installed a chart of account.'))
        to_open_invoices.action_date_assign()
        to_open_invoices.action_move_create()
        return to_open_invoices.invoice_validate()


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
    def _transporte(self):
        if self.ind_servicio!=4:
            aduana={}
            TipoBultos=[]
            for t in self.bultos:
                TipoBultos.append(
                                    {
                                        "CodigoTipoBulto":t.tipo_bulto.code,
                                        "CantidadBultos":t.cantidad_bultos,
                                        "IdContainer":t.id_container,
                                        "Sello":t.sello,
                                        "EmisorSello":t.emisor_sello
                                    }
                                )

            aduana={
                        "CodigoModalidadVenta":self.payment_term_id.modalidad_venta.code,
                        "CodigoClausulaVenta":self.clausula_venta.code,
                        "TotalClausulaVenta":self.amount_total,
                        "CodigoViaTransporte":self.via.code,
                        "CodigoPuertoEmbarque":self.puerto_embarque.code,
                        "CodigoPuertoDesembarque":self.puerto_desembarque.code,
                        "Tara":self.tara,
                        "CodigoUnidadMedidaTara":self.uom_tara.code,
                        "PesoBruto":self.peso_bruto,
                        "CodigoUnidadPesoBruto":self.uom_peso_bruto.code,
                        "PesoNeto":self.peso_neto,
                        "CodigoUnidadPesoNeto":self.uom_peso_bruto.code,
                        "CantidadBultos":self.total_bultos,
                        "TipoBultos":TipoBultos,
                        "MontoFlete":self.monto_flete,
                        "MontoSeguro":self.monto_seguro,
                        "CodigoPaisReceptor":self.pais_id.code_dte,
                        "CodigoPaisDestino":self.pais_destino.code
                    }
            aduana.update(aduana)
            return aduana
        else:
            return None


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
                if self.document_class_id.sii_code==43:
                    detalle['TipoDocumentoLiquidacion']="39"
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
            return []

    @api.model
    def _obtener_referencias(self):
        if self.referencias:
            referencias={}
            for l in self.referencias:
                referencia={
                    "FechaDocumentoReferencia": l.fecha_documento.isoformat(),
                    "TipoDocumento": l.sii_referencia_TpoDocRef.sii_code,
                    "CodigoReferencia": l.sii_referencia_CodRef,
                    "RazonReferencia": l.motivo,
                    "FolioReferencia": l.origen
                }
                referencias.update(referencia)

            return referencias
        else:
            return None

    @api.model
    def _obtener_datos_liquidacion_factura(self,folio):
        compañia=self.env.user.company_id
        codigos_actividad=[]
        for a in self._obtener_acteco():
            codigos_actividad.append(a[0])
        payload = {
            "Liquidacion": {
            "Encabezado": {
                "IdentificacionDTE": {
                    "TipoDTE": self.document_class_id.sii_code,
                    "Folio":folio,
                    "FechaEmision": self.date_invoice.isoformat(),
                    "FechaVencimiento": self.date_due.isoformat(),
                    "FormaPago": self.payment_term_id.dte_sii_code if self.payment_term_id.dte_sii_code else 1
                },
                "Emisor": {
                    "Rut": compañia.partner_id.document_number.replace('.',''),
                    "RazonSocial": compañia.partner_id.name,
                    "Giro": compañia.partner_id.activity_description.name,
                    "ActividadEconomica": codigos_actividad,
                    "DireccionOrigen": compañia.partner_id.street,
                    "ComunaOrigen": compañia.partner_id.city_id.name,
                    "Telefono": [compañia.partner_id.phone if compañia.partner_id.phone else 0]

                },
                "Receptor": {
                    "Rut": self.partner_id.document_number[1:].replace(".","") if self.partner_id.document_number[:1]=="0" else self.partner_id.document_number.replace(".",""),
                    "RazonSocial": self.partner_id.name,
                    "Direccion": self.partner_id.street if self.partner_id.street else None,
                    "Comuna": self.partner_id.city_id.name if self.partner_id.city_id.name else None,
                    "Ciudad": self.partner_id.city if self.partner_id.city else None,
                    "Giro": self.partner_id.activity_description.name if self.partner_id.activity_description.name else None,
                    "Contacto": self.partner_id.mobile if self.partner_id.mobile else '',
                    "CorreoElectronico": self.partner_id.email if self.partner_id.email else ''
                },
                "Totales": {
                    "MontoNeto": round(self.amount_untaxed),
                    "TasaIVA": 19,
                    "IVA": round(self.amount_tax),
                    "MontoTotal": round(self.amount_total),
                    "Comisiones": [
                        {
                        "ValorNeto": round(self.neto_comision),
                        "ValorExento": 0,
                        "ValorIVA": round(self.iva_comision)
                        }
                    ]
                }
            },
            "Detalles":self._obtener_lineas(),
            "Comisiones": [
                {
                    "TipoMovimiento": "Comision",
                    "Glosa": "Comision",
                    "Tasa": self.porc_comision,
                    "ValorNeto": round(self.neto_comision),
                    "ValorExento": 0,
                    "ValorIVA": round(self.iva_comision)
                }
            ]
        }
        }        
        return payload


    @api.one
    def _generar_xml(self):
        if self.document_class_id.sii_code in(46,110,112,43):
            compañia=self.env.user.company_id
            ruta_certificado=compañia.simple_api_ruta_certificado
    #Obtiene folios desde la clase de documentos        
            journal_document_class_id=self.env['account.journal.sii_document_class'].search([('sii_document_class_id','=',self.document_class_id.id)])         

            domain=[('sii_code','=',self.document_class_id.sii_code),
            ('journal_id','=',self.journal_id.id),
            ('sii_document_number','!=',False),
            ('id','!=',self.id),            
            ]
            if self.sii_document_number==0 and self.document_class_id.sii_code ==46:
                folio=self.env['account.invoice'].search(domain,order="sii_document_number desc", limit=1).sii_document_number
                folio+=1
            else:
                folio=self.sii_document_number

            codigos_actividad=[]
            for a in self._obtener_acteco():
                codigos_actividad.append(a[0])

            if self.use_documents and self.document_class_id.sii_code ==46: 
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
                            "Direccion": self.partner_id.street if self.partner_id.street else None,
                            "Comuna": self.partner_id.city_id.name if self.partner_id.city_id.name else None,
                            "Giro": self.partner_id.activity_description.name if self.partner_id.activity_description.name else None,
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
                # payload["Certificado"]=self._get_certificado(compañia)            
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
            elif self.document_class_id.sii_code in(110,112,43):
                if self.document_class_id.sii_code in(110,112):
                    payload={
                    "Exportaciones":{
                        "Encabezado":{
                            "IdentificacionDTE":{
                                "TipoDTE":self.document_class_id.sii_code,
                                "Folio":folio,
                                "FechaEmision":self.date_invoice.isoformat(),
                                "FechaVencimiento":self.date_due.isoformat(),
                                "FormaPago":self.payment_term_id.dte_sii_code,
                                "FormaPagoExportacion":self.payment_term_id.forma_pago_aduanas.code if self.document_class_id.sii_code in(110,112) else '',
                                "MedioPago":self.payment_term_id.modalidad_venta.code if self.document_class_id.sii_code in(110,112) else '',
                                "IndServicio":self.ind_servicio
                            },

                            "Emisor": {
                                "Rut": compañia.partner_id.document_number.replace('.',''),
                                "RazonSocial": compañia.partner_id.name,
                                "Giro": compañia.partner_id.activity_description.name,
                                "ActividadEconomica": codigos_actividad,
                                "DireccionOrigen": compañia.partner_id.street,
                                "ComunaOrigen": compañia.partner_id.city_id.name,
                                "Telefono": [compañia.partner_id.phone if compañia.partner_id.phone else 0]
                            },

                            "Receptor": {
                                "Rut": '55555555-5',
                                "RazonSocial": self.partner_id.name,
                                "Direccion": self.partner_id.street if self.partner_id.street else compañia.partner_id.street,
                                "Comuna": self.partner_id.city_id.name if self.partner_id.city_id.name else compañia.partner_id.city_id.name,
                                "Giro": self.partner_id.activity_description.name if self.partner_id.activity_description.name else compañia.partner_id.activity_description.name,
                                "Extranjero":{
                                "Nacionalidad":self.pais_id.code_dte if self.pais_id else '997'
                                }
                            },
                            "Transporte":{"Aduana":self._transporte()[0]},                    
                            
                            "Totales":{
                                "TipoMoneda":"DOLAR_ESTADOUNIDENSE",
                                "MontoExento":round(self.amount_total,0) ,
                                "MontoTotal":round(self.amount_total,0)
                            },
                            "OtraMoneda":{
                                "TipoMoneda":"PESO_CHILENO",
                                "TipoCambio":self.currency_id.inverse_rate,
                                "MontoExento":round(self.amount_total*self.currency_id.inverse_rate,0),
                                "MontoTotal":round(self.amount_total*self.currency_id.inverse_rate,0) 
                            }
                        },
                        "Detalles":self._obtener_lineas(),
                        "DescuentosRecargos":self._obtener_DR(),
                    },
                    }
                elif self.document_class_id.sii_code ==43:
                    payload=self._obtener_datos_liquidacion_factura(folio,)
                
                print(payload)

                payload["Certificado"]=self._get_certificado(compañia)    

    #Agrega las referencias del documento            
                if self.referencias:
                    payload["Referencias"]=self._obtener_referencias()
                # if self.global_descuentos_recargos:
                #     payload["DescuentosRecargos"]=self._obtener_DR()
                
                json_payload=json.dumps(payload)     

                files=self._firmar_Timbrar_xml(payload,compañia)   
                response = self.generar_xml_dte(files,folio)
                if response!=False:
                    sobre=self.generar_sobre_envio(response[1],compañia,folio,receptor='60803000-K')
                    if sobre!=False:
                        envio=self.enviar_sobre_envio(sobre[1],compañia,tipo=1)
                        dict_text = json.loads(envio.text)  
                        if envio.status_code==200:
                            self.sii_message=dict_text['responseXml']

                            self.sii_result='Enviado'
                            self.sii_document_number=folio

                            nombre_archivo=self._obtener_nombre_xml(response[1])
                            with open(response[1], 'r',encoding='utf-8',errors='ignore') as f:
                                try:
                                    # text = f.decode('utf8')
                                    # dte_envio = text.read()
                                    dte_envio = f.read()
                                except Exception as e:
                                    print(e)
                                

                            if not self.sii_xml_request:
                                envio_id = self.env["sii.xml.envio"].create({
                                        'name': nombre_archivo,
                                        'xml_envio': dte_envio,
                                        'invoice_ids': [[6,0, self.ids]],
                                    })      
                            self.write({
                                'state':'open',
                                'sii_track_id':dict_text['trackId']
                            })
                            tree = ET.parse(response[1])

                            root = tree.getroot()
                            if self.document_class_id.sii_code in(110,112):      
                                tag = root.find("Exportaciones")                                  
                            elif self.document_class_id.sii_code ==43:
                                tag = root.find("Liquidacion")  
                            else:
                                tag = root.find("Documento")  


                            ted=tag.find("TED")
                            tag_string = ET.tostring(ted, encoding='utf8', method='xml')
                            self.sii_barcode=tag_string
                            self._get_barcode_img()
            #Actualiza secuencia
                            secuencia=self.env['ir.sequence'].search([('sii_document_class_id','=',self.document_class_id.id)])
                            secuencia.write({
                                                'number_next_actual':folio+1
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
        if self.document_class_id.sii_code !=43:
            url = compañia.simple_api_servidor+"/api/v1/dte/generar"
        else:
            url=compañia.simple_api_servidor+"/api/v1/dte/liquidacion/generar"

        response = requests.post(url, headers=headers, files=files)
        if response.status_code==200:
            pathDTE = os.path.join(compañia.simple_api_ruta_dte,'DTE_'+str(self.document_class_id.sii_code)+'_'+compañia.partner_id.document_number.replace('.','')+'_'+str(folio)+'.xml' )
            with codecs.open(pathDTE,'w+',"ISO-8859-1") as f:            
                f.write(response.text)
                dte=f.read()
            return response.text,pathDTE
        else:
            raise Warning("Problemas para generar XML, el error es : "+response.text)
            return False

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
        files=self._firmar_Timbrar_xml_sobre(payload,company,pathDTE)

        headers = {
                'Authorization': company.simple_api_token,
            }        

        response = requests.post(url, headers=headers, files=files)
        if response.status_code==200:
            pathDTE = os.path.join(company.simple_api_ruta_dte,'Envio_DTE_'+str(self.document_class_id.sii_code)+'_'+company.partner_id.document_number.replace('.','')+'_'+str(folio)+'.xml' )

            with codecs.open(pathDTE, 'w+', encoding='iso-8859-1') as f:
                f.write(response.text)
            with codecs.open(pathDTE, 'r+', encoding='iso-8859-1') as f:
                dte=f.read()
            self.sii_xml_dte= dte        
            return response,pathDTE
        else:
            raise Warning("Problemas para generar sobre de envío, el mensaje es :" + response.text)
            return False

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
        print(response.text)
        if response.status_code==200:
            return response
        else:
            raise Warning("Problemas para generar sobre de envío, el mensaje es :" + response.text)
            return False


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
        posicion=(pathDTE.find('Envio_'))
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
        archivo_caf=caf.obtener_caf(self.sii_document_number)
        nombre_caf=archivo_caf[0]['name']
        ruta_completa_caf=compañia.simple_api_ruta_caf+nombre_caf
        files = [
                ('input', ('', json.dumps(payload), 'application/json')),
                # ('input', (json.dumps(payload), 'application/json')),
                ('files', (compañia.simple_api_nombre_certificado, open(compañia.simple_api_ruta_certificado+compañia.simple_api_nombre_certificado, 'rb'), 'application/x-pkcs12')),
                ('files', (nombre_caf, open(ruta_completa_caf, 'rb'), 'text/xml')),
            ]            

        return files