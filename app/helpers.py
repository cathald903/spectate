"""
Some convienient helper funcs
"""

import urllib.parse
import re
from sqlalchemy import text
from .db import db
##############################
###     Helper Funcs       ###
##############################


def execute_query(cmd: str, params=None):
    """
    Connects to the db and tries to execute the given command, rolling back
    if failed
    """
    with db.connect() as connection:
        conn = connection.begin()
        try:
            if params:
                connection.execute(text(cmd), params)
            else:
                connection.execute(text(cmd))
            conn.commit()  # Commit if success
            return True
        except RuntimeError as e:
            print(e)
            conn.rollback()  # Roll back if error
            return False


def select_query(cmd: str, params=None):
    """
    Connects to the db and tries to execute the given select query
    """
    with db.connect() as connection:
        conn = connection.begin()
        try:
            if params:
                res = connection.execute(text(cmd), params).fetchall()
                res = [list(row) if len(row) else [] for row in res]
            else:
                res = connection.execute(text(cmd)).fetchall()
                res = [list(row) if len(row) else [] for row in res]
            conn.commit()  # Commit if success
            return res
        except RuntimeError as e:
            print(e)
            return False


def url_friendly_version(name: str):
    """
    Derives the url friendly version of the given name
    """
    sanitized = re.sub(r'[^\w\s-]', '', name)
    hyphenated = re.sub(r'[\s_]+', '-', sanitized)
    lowercased = hyphenated.lower()
    url_friendly = urllib.parse.quote(lowercased)
    return url_friendly


def get_simple_sql_operator(operator: str):
    """
    user input -> SQL operator quick reference
    """
    simple_operators = {
        "equal": "=",
        "not_equal": "!=",
        "less_than": "<",
        "greater_than": ">",
        "lequal": "<=",
        "gequal": ">="
    }
    return simple_operators[operator]
