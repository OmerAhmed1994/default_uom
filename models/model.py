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

    @api.multi
    def _prepare_stock_moves(self, picking):
        """ Prepare the stock moves data for one order line. This function returns a list of
        dictionary ready to be used in stock.move's create()
        """
        self.ensure_one()
        res = []
        if self.product_id.type not in ['product', 'consu']:
            return res
        qty = 0.0
        price_unit = self._get_stock_move_price_unit()
        for move in self.move_ids.filtered(lambda x: x.state != 'cancel' and not x.location_dest_id.usage == "supplier"):
            qty += move.product_uom._compute_quantity(
                move.product_uom_qty, self.product_uom, rounding_method='HALF-UP')
        template = {
            # truncate to 2000 to avoid triggering index limit error
            # TODO: remove index in master?
            'name': (self.name or '')[:2000],
            'product_id': self.product_id.id,
            'product_uom': self.product_uom.id,
            'product_uom_qty': self.product_qty,
            'date': self.order_id.date_order,
            'date_expected': self.date_planned,
            'location_id': self.order_id.partner_id.property_stock_supplier.id,
            'location_dest_id': self.order_id._get_destination_location(),
            'picking_id': picking.id,
            'partner_id': self.order_id.dest_address_id.id,
            'move_dest_ids': [(4, x) for x in self.move_dest_ids.ids],
            'state': 'draft',
            'purchase_line_id': self.id,
            'company_id': self.order_id.company_id.id,
            'price_unit': price_unit,
            'picking_type_id': self.order_id.picking_type_id.id,
            'group_id': self.order_id.group_id.id,
            'origin': self.order_id.name,
            'route_ids': self.order_id.picking_type_id.warehouse_id and [(6, 0, [x.id for x in self.order_id.picking_type_id.warehouse_id.route_ids])] or [],
            'warehouse_id': self.order_id.picking_type_id.warehouse_id.id,
        }
        # diff_quantity = self.product_qty - qty
        # if float_compare(diff_quantity, 0.0,  precision_rounding=self.product_uom.rounding) > 0:
        #     quant_uom = self.product_id.uom_id
        #     get_param = self.env['ir.config_parameter'].sudo().get_param
        #     # Always call '_compute_quantity' to round the diff_quantity. Indeed, the PO quantity
        #     # is not rounded automatically following the UoM.
        #     if get_param('stock.propagate_uom') != '1':
        #         product_qty = self.product_uom._compute_quantity(
        #             diff_quantity, quant_uom, rounding_method='HALF-UP')
        #         template['product_uom'] = quant_uom.id
        #         template['product_uom_qty'] = product_qty
        #     else:
        #         template['product_uom_qty'] = self.product_uom._compute_quantity(
        #             diff_quantity, self.product_uom, rounding_method='HALF-UP')
        res.append(template)
        return res


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
        res = super(StockInventoryLine, self)._onchange_product()
        if self.product_id:
            self.product_uom_id = self.product_id.get_sale_default_uom_id()
        if res.get('domain') and self.product_id:
            if res['domain'].get('product_uom_id'):
                res['domain']['product_uom_id'] = [
                    ('id', 'in', self.product_id.get_domain_ids())]
        return res
