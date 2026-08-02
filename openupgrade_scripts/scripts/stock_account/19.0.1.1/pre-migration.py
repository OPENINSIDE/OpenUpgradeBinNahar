# Copyright 2026 Hunki Enterprises BV
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


_renamed_models = [
    ("stock.valuation.layer", "product.value"),
]

_renamed_tables = [
    ("stock_valuation_layer", "product_value"),
]

_renamed_fields = [
    ("product.value", "product_value", "", ""),
]

_copied_columns = {
    "product_value": [
        ("create_date", "date", None),
        ("create_uid", "user_id", None),
        ("stock_move_id", "move_id", None),
    ],
}

_deleted_xmlids = [
    "stock_account.stock_valuation_layer_company_rule",
    "stock_account.group_stock_accounting_automatic",
]


def stock_lot_avg_cost(env):
    """
    Precreate stock.lot#avg_cost to avoid compute method
    """
    openupgrade.add_fields(
        env,
        [
            ("avg_cost", "stock.lot", "stock_lot", "float", None, "stock_account", 0),
        ],
    )


def stock_move_is_fields(env):
    """
    Precreate stock.move#is_* to avoid compute method
    """
    openupgrade.add_fields(
        env,
        [
            (
                "is_in",
                "stock.move",
                "stock_move",
                "boolean",
                None,
                "stock_account",
                False,
            ),
            (
                "is_out",
                "stock.move",
                "stock_move",
                "boolean",
                None,
                "stock_account",
                False,
            ),
            (
                "is_dropship",
                "stock.move",
                "stock_move",
                "boolean",
                None,
                "stock_account",
                False,
            ),
        ],
    )

def copy_product_value_columns(env):
    """
    Copy product.value columns to avoid compute method
    """
    env.cr.execute("ALTER TABLE product_value ADD COLUMN date timestamp without time zone")
    env.cr.execute("ALTER TABLE product_value ADD COLUMN user_id integer")
    env.cr.execute("ALTER TABLE product_value ADD COLUMN move_id integer")
    explode_execute(
        env.cr,
        """
UPDATE product_value SET
date=create_date,
user_id=create_uid,
move_id=stock_move_id
        """,
        table="product_value",
    )

@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_models(env.cr, _renamed_models)
    openupgrade.rename_tables(env.cr, _renamed_tables)
    openupgrade.rename_fields(env, _renamed_fields)
    #openupgrade.copy_columns(env.cr, _copied_columns)
    copy_product_value_columns(env)
    openupgrade.delete_records_safely_by_xml_id(env, _deleted_xmlids)
    stock_lot_avg_cost(env)
    stock_move_is_fields(env)
