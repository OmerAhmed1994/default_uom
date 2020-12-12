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
        'uom.uom', 'Default Unit of Measure')
    
    default_uom_qty_available = fields.Float(
        compute='_compute_default_uom_qty_available', string='Quantity Available')
    
    @api.depends('default_uom_id', 'uom_id')
    def _compute_default_uom_qty_available(self):
        for rec in self:
            rec.default_uom_qty_available = 0
            if rec.uom_id and rec.default_uom_id:
                rec.default_uom_qty_available = rec.uom_id._compute_quantity(
                    rec.qty_available, rec.default_uom_id)


class ProductProduct(models.Model):
    _inherit = "product.product"

    def get_domain_ids(self):
        if self.default_uom_id:
            return list(set([self.default_uom_id.id, self.uom_id.id, self.uom_po_id.id]))
        return list(set([self.uom_id.id, self.uom_po_id.id]))

    def get_sale_default_uom_id(self):
        if self.env.user.company_id.default_uom:
            return self.default_uom_id.id if self.default_uom_id else self.uom_id.id
        return self.uom_id.id

    def get_purchase_default_uom_id(self):
        if self.env.user.company_id.default_uom:
            return self.default_uom_id.id if self.default_uom_id else self.uom_po_id.id
        return self.uom_po_id.id

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
        if res.get('domain') and self.product_id:
            if res['domain'].get('uom_id'):
                res['domain']['uom_id'] = [
                    ('id', 'in', self.product_id.get_domain_ids())]
        return res

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        res = super(SaleOrderLine, self).product_id_change()
        if self.product_id:
            self.product_uom = self.product_id.get_sale_default_uom_id()
        if res.get('domain') and self.product_id:
            if res['domain'].get('product_uom'):
                res['domain']['product_uom'] = [
                    ('id', 'in', self.product_id.get_domain_ids())]
        return res


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.onchange('product_id')
    def onchange_product_id(self):
        res = super(PurchaseOrderLine, self).onchange_product_id()
        if self.product_id:
            self.product_uom = self.product_id.get_purchase_default_uom_id()
        if res.get('domain') and self.product_id:
            if res['domain'].get('product_uom'):
                res['domain']['product_uom'] = [
                    ('id', 'in', self.product_id.get_domain_ids())]
        return res


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.onchange('product_id')
    def onchange_product_id(self):
        res = super(StockMove, self).onchange_product_id()
        if self.product_id:
            self.product_uom = self.product_id.get_sale_default_uom_id()
        if res.get('domain') and self.product_id:
            if res['domain'].get('product_uom'):
                res['domain']['product_uom'] = [
                    ('id', 'in', self.product_id.get_domain_ids())]
        return res


class StockInventoryLine(models.Model):
    _inherit = 'stock.inventory.line'

    @api.onchange('product_id')
    def _onchange_product(self):
        res = super(StockInventoryLine, self).onchange_product_id()
        if self.product_id:
            self.product_uom_id = self.product_id.get_sale_default_uom_id()
        if res.get('domain') and self.product_id:
            if res['domain'].get('product_uom_id'):
                res['domain']['product_uom_id'] = [
                    ('id', 'in', self.product_id.get_domain_ids())]
        return res
