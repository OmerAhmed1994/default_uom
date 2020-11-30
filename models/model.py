# -*- coding: utf-8 -*-
import logging
from odoo.osv import expression
import re
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons import decimal_precision as dp

class ProductTemplate(models.Model):
    _inherit = "product.template"

    default_uom_id = fields.Many2one(
        'uom.uom', 'Default Sale Unit of Measure')
    default_uom_po_id = fields.Many2one(
        'uom.uom', 'Default Purchase Unit of Measure')


class ProductProduct(models.Model):
    _inherit = "product.product"

    def get_sale_default_uom_id(self):
        if self.env.user.company_id.default_uom:
            return self.default_uom_id.id if self.default_uom_id else self.uom_id.id

    def get_purchase_default_uom_id(self):
        if self.env.user.company_id.default_uom:
            return self.default_uom_po_id.id if self.default_uom_po_id else self.uom_po_id.id
        
class ResCompany(models.Model):
    _inherit = "res.company"
    
    default_uom = fields.Boolean()


class AcconutInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    @api.onchange('product_id')
    def _onchange_product_id(self):
        res = super(AcconutInvoiceLine, self)._onchange_product_id()
        if self.invoice_id.type in ['out_refand', 'out_invoice'] and self.product_id:
            self.uom_id = self.product_id.get_sale_default_uom_id()
        elif self.invoice_id.type in ['in_refand', 'in_invoice'] and self.product_id:
            self.uom_id = self.product_id.get_purchase_default_uom_id()
        return res


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        res = super(SaleOrderLine, self).product_id_change()
        if self.product_id:
            self.product_uom = self.product_id.get_sale_default_uom_id()
        return res


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.onchange('product_id')
    def onchange_product_id(self):
        res = super(PurchaseOrderLine, self).onchange_product_id()
        if self.product_id:
            self.product_uom = self.product_id.get_purchase_default_uom_id()
        return res
