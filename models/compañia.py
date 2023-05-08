# -*- coding: utf-8 -*-

from odoo import models, fields, api
from http.client import HTTPSConnection
from base64 import b64encode

class Company(models.Model):
    _inherit = 'res.company'

    simple_api_servidor = fields.Char('URL Servidor')
    simple_api_usuario = fields.Char('Usuario Simple API')
    simple_api_password = fields.Char('Password Simple API')
    simple_api_token = fields.Char('Token Simple API')
    simple_api_ruta_certificado = fields.Char('Ruta del certificado',placeholder='c:\directorio')
    simple_api_nombre_certificado = fields.Char('Nombre del certificado',placeholder='certiicado.pfk')
    simple_api_rut_certificado = fields.Char('Rut Certificado')
    simple_api_password_certificado = fields.Char('Password Certificado')
    simple_api_ruta_dte = fields.Char('Ruta Dte',placeholder='c:\directorio')
    simple_api_ruta_caf = fields.Char('Ruta CAF',placeholder='c:\directorio')

    @api.model
    def _certificar(self,compañia):
        files = [
                ('files', (compañia.simple_api_nombre_certificado, open(compañia.simple_api_ruta_certificado+'\\'+compañia.simple_api_nombre_certificado, 'rb'), 'application/x-pkcs12')),
            ]            

        return files  

    @api.model
    def _get_certificado(self,compañia):
        certificado={
                    "Rut": compañia.simple_api_rut_certificado,
                    "Password": compañia.simple_api_password_certificado
                }    
        return certificado   

    def basic_auth(self):
        token = b64encode(f"{self.simple_api_usuario}:{self.simple_api_password}".encode('utf-8')).decode("ascii")
        self.simple_api_token= f'Basic {token}'
    