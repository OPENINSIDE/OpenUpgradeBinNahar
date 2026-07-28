# Copyright 2025 Tecnativa - Carlos Lopez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
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

def _adjust_stock_picking_batch_sequence(env):
    """As the order in the tree view and report is now by batch_sequence,
    we need to set the batch_sequence field
    to maintain the same order as in the previous version,
    because this new field does not have a default value.
    The order is taken from the picking model.
    """
    explode_execute(
        env.cr,
        """
        UPDATE stock_picking sp
        SET batch_sequence = sub.row_number
        FROM (
            SELECT id, row_number()
            OVER (
                PARTITION BY batch_id
                ORDER BY priority desc, scheduled_date asc, id desc
            )
            FROM stock_picking
        ) as sub
        WHERE sub.id = sp.id
        """,
        table="stock_picking",
        alias="sp"
    )


@openupgrade.migrate()
def migrate(env, version):
    _adjust_stock_picking_batch_sequence(env)
