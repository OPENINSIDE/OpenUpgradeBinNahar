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

_new_columns = [
    ("sale.order.line", "warehouse_id", "many2one"),
]


def fill_sale_order_line_warehouse_id(env):
    explode_execute(
        env.cr,
        """
        UPDATE sale_order_line sol
        SET warehouse_id = so.warehouse_id
        FROM sale_order so
        WHERE sol.order_id = so.id AND sol.route_id IS NULL
        """,
        table="sale_order_line",
        alias="sol",
    )
    explode_execute(
        env.cr,
        """
        WITH sub as (
              SELECT sr.route_id, sr.location_dest_id, sl.warehouse_id
              FROM stock_rule sr
              JOIN stock_route slr ON sr.route_id = slr.id
              LEFT JOIN stock_location sl ON sr.location_src_id = sl.id
              WHERE sr.action != 'push'
              ORDER BY sr.route_sequence, sr.sequence
        )
        UPDATE sale_order_line sol2
        SET warehouse_id = COALESCE(
            sub1.warehouse_id, sub2.warehouse_id, so.warehouse_id)
        FROM sale_order_line sol
        JOIN sale_order so ON sol.order_id = so.id
        LEFT JOIN res_partner rp ON so.partner_shipping_id = rp.id
        LEFT JOIN stock_location sl ON sl.id = (
            rp.property_stock_customer::jsonb -> so.company_id)::int4
        LEFT JOIN LATERAL (
            SELECT sub.warehouse_id
            FROM sub
            WHERE sol.route_id = sub.route_id AND
                sub.location_dest_id = sl.id AND (
                    sub.warehouse_id IS NULL OR so.warehouse_id = sub.warehouse_id)
            LIMIT 1
        ) sub1 ON TRUE
        LEFT JOIN LATERAL (
            SELECT sub.warehouse_id
            FROM sub
            WHERE sol.route_id = sub.route_id AND
                sub.location_dest_id = sl.id
            LIMIT 1
        ) sub2 ON TRUE
        WHERE sol.id = sol2.id AND sol.route_id IS NOT NULL
        """,
        table="sale_order_line",
        alias="sol2",
    )


@openupgrade.migrate()
def migrate(env, version=None):
    openupgrade.add_columns(env, _new_columns)
    fill_sale_order_line_warehouse_id(env)
