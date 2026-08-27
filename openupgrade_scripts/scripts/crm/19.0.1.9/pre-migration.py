# Copyright 2026 Tecnativa - Eduardo Ezerouali
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


def _won_status_set(env):
    # Precreate won_status and set with sql
    openupgrade.add_columns(
        env,
        [
            ("crm.lead", "won_status", "selection", "pending", "crm_lead"),
        ],
    )
    explode_execute(
        env.cr,
        """
        UPDATE crm_lead cl
        SET won_status = 'won'
        FROM crm_stage cs
        WHERE cs.id = cl.stage_id
        AND cs.is_won
        AND cl.probability = 100
        """,
        table="crm_lead",
        alias="cl"
    )
    explode_execute(
        env.cr,
        """
        UPDATE crm_lead cl
        SET won_status = 'lost'
        WHERE NOT cl.active
        AND cl.probability = 0
        """,
        table="crm_lead",
        alias="cl"
    )


@openupgrade.migrate()
def migrate(env, version):
    _won_status_set(env)
