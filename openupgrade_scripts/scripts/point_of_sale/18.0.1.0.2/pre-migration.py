# Copyright 2025 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from openupgradelib import openupgrade

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


def set_pos_printer_company_id(env):
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE pos_printer pp
        SET company_id = COALESCE(pp.company_id, pc.company_id)
        FROM pos_config pc
        JOIN pos_config_printer_rel rel ON rel.config_id = pc.id
        WHERE rel.printer_id = pp.id AND pc.active
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE pos_printer pp
        SET company_id = COALESCE(pp.company_id, pc.company_id)
        FROM pos_config pc
        JOIN pos_config_printer_rel rel ON rel.config_id = pc.id
        WHERE rel.printer_id = pp.id AND pc.active IS DISTINCT FROM TRUE
        """,
    )
    openupgrade.logged_query(
        env.cr,
        f"""
        UPDATE pos_printer pp
        SET company_id = {env.company.id}
        WHERE pp.company_id IS NULL
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_fields(
        env,
        [
            ("pos.category", "pos_category", "child_id", "child_ids"),
            ("pos.order", "pos_order", "note", "floating_order_name"),
            (
                "pos.config",
                "pos_config",
                "iface_customer_facing_display_background_image_1920",
                "customer_display_bg_img_name",
            ),
        ],
    )
    if openupgrade.column_exists(env.cr, "product_template", "description_self_order"):
        # from pos_self_order
        openupgrade.rename_fields(
            env,
            [
                (
                    "product.template",
                    "product_template",
                    "description_self_order",
                    "public_description",
                ),
            ],
        )
    openupgrade.add_columns(
        env,
        [
            ("pos.order", "amount_difference", "float", None, "pos_order"),
            ("pos.order.line", "price_type", "selection", "original", "pos_order_line"),
            ("pos.printer", "company_id", "many2one", None, "pos_printer"),
        ],
    )
    explode_execute(
        env.cr,
        """
        UPDATE pos_order
        SET amount_difference = amount_paid - amount_total
        """,
        table="pos_order",
    )
    set_pos_printer_company_id(env)
