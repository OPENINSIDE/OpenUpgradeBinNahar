# Copyright 2025 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from openupgradelib import openupgrade

from odoo.upgrade import util
import logging
import datetime
from odoo.sql_db import db_connect
_logger = logging.getLogger(__name__)

def explode_execute(cr, query, *args, **kwargs):
    _logger.info("Execute a query in parallel: %s", query)
    cr.commit()  # Commit the current transaction before executing in parallel
    with db_connect(cr.dbname).cursor() as cr2:
        start_time = datetime.datetime.now()
        util.explode_execute(cr2, query, *args, **kwargs)
        end_time = datetime.datetime.now()
        _logger.info("Query executed in parallel in %s", (end_time - start_time))

@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_fields(
        env,
        [("product.document", "product_document", "attached_on", "attached_on_sale")],
    )
    openupgrade.rename_xmlids(
        env.cr,
        [
            (
                "sale.sale_order_action_view_quotation_kanban",
                "sale.action_quotations_kanban",
            ),
            (
                "sale.sale_order_action_view_quotation_tree",
                "sale.action_quotations_tree",
            ),
        ],
    )
    openupgrade.add_columns(
        env,
        [("sale.order.line", "technical_price_unit", "float", None, "sale_order_line")],
    )
    explode_execute(
        env.cr,
        """
        UPDATE sale_order_line
        SET technical_price_unit = price_unit
        """,
        table="sale_order_line",
    )
    openupgrade.delete_sql_constraint_safely(
        env, "sale", "sale_order_line", "accountable_required_fields"
    )
