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


def product_value_product_id(env):
    """
    Fill product.value#product_id from move_id.product_id
    """
    explode_execute(
        env.cr,
        """
        UPDATE product_value
        SET product_id=stock_move.product_id
        FROM stock_move
        WHERE product_value.move_id=stock_move.id
        AND product_value.product_id IS NULL
        """,
        table="product_value",
    )


def stock_move_account_move_id(env):
    """
    Fill stock.move#account_move_id from account.move#stock_move_id
    """
    explode_execute(
        env.cr,
        """
        UPDATE stock_move
        SET account_move_id=account_move.id
        FROM account_move
        WHERE
        account_move.stock_move_id=stock_move.id
        AND stock_move.account_move_id IS NULL
        """,
        table="stock_move",
    )


def product_category_property_valuation(env):
    """
    Change value 'manual_periodic' to 'periodic'
    """
    env["ir.default"].search(
        [
            ("field_id.name", "=", "property_valuation"),
            ("field_id.model_id.model", "=", "product.category"),
            ("json_value", "=", '"manual_periodic"'),
        ]
    ).write({"json_value": '"periodic"'})

    for company in env["res.company"].search([]):
        env.cr.execute(
            f"""
            UPDATE product_category
            SET
            property_valuation = property_valuation || '{{"{company.id}": "periodic"}}'
            WHERE
            property_valuation->>'{company.id}' = 'manual_periodic'
            """
        )


def stock_location_valuation_account_id(env):
    """
    Set stock.location#valuation_account_id from valuation_in_account_id and
    valuation_out_account_id if they are the same
    """
    env.cr.execute(
        """
        UPDATE stock_location
        SET valuation_account_id=valuation_in_account_id
        WHERE
        valuation_in_account_id=valuation_out_account_id
        """
    )


def stock_move_value(env):
    """
    Set stock.move#value to sum of product.value#value for this move
    """
    explode_execute(
        env.cr,
        """
        UPDATE stock_move
        SET value=aggregated_values.value
        FROM (
            SELECT
            move_id, sum(value) value
            FROM
            product_value
            GROUP BY move_id
        ) aggregated_values
        WHERE aggregated_values.move_id=stock_move.id
        """,
        table="stock_move",
    )


@openupgrade.migrate()
def migrate(env, version):
    product_value_product_id(env)
    stock_move_account_move_id(env)
    product_category_property_valuation(env)
    stock_location_valuation_account_id(env)
    stock_move_value(env)
