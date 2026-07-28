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


def fill_purchase_order_amount_total_cc(env):
    explode_execute(
        env.cr,
        """
        UPDATE purchase_order
        SET amount_total_cc = amount_total / currency_rate
        WHERE COALESCE(currency_rate, 0) != 0""",
        table="purchase_order",
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.delete_sql_constraint_safely(
        env, "purchase", "purchase_order_line", "accountable_required_fields"
    )
    openupgrade.add_columns(
        env, [("purchase.order", "amount_total_cc", "float", None, "purchase_order")]
    )
    fill_purchase_order_amount_total_cc(env)
