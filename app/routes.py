"""
Definitions of all the app routes
"""
import json
from flask import Blueprint, request
from .helpers import select_query
from .tables import determine_tab_class, clear_tables, declare_tables
from .modify_db import insert_cmd, update_cmd, delete_cmd, inactive_check
from .sanity import parse_dict
from .sql_funcs import sqlify


main = Blueprint('main', __name__)

##############################
###     Routes             ###
##############################


@main.route('/')
def homepage():
    """
    Displays what is currently in all the tables in plaintext on the homepage
    """
    res = []
    for obj in ['Sport', 'Event', 'Selection']:
        cmd = f"Select * from {obj}"
        r = select_query(cmd)
        res.append(f"{obj}s:")
        res.append(r)
    return res


@main.route('/modify_object', methods=['POST'])
def modify_object():
    """
    Decides which operation eg insert,update,delete needs to be carried out on
    the given input, limited explicitly to the Sport,Event and Selection table
    """
    request_dict = json.loads(request.data)
    table, kind = [request_dict['object'], request_dict['kind']]
    if not table in ['Sport', 'Event', 'Selection'] or not kind in ['create', 'update', 'delete']:
        return "Invalid 'object' and/or 'kind' value "
    obj = determine_tab_class(table)
    obj = obj()
    update_dict = parse_dict(obj, request_dict)
    try:
        if kind == 'create':
            insert_cmd(table, obj, update_dict)
        elif kind == 'update':
            update_cmd(table, update_dict)
        else:
            delete_cmd(table, update_dict)
    except RuntimeError as e:
        print(e)
        return str(e)
    if request_dict['object'] in ['Event', 'Selection']:
        inactive_check(request_dict['object'], update_dict)

    return request_dict['Name'] + ": Updated"


@main.route('/filter_object', methods=['POST'])
def filter_object():
    """
    Parses the given dict into it's sql counterpart
    """
    request_dict = json.loads(request.data)
    res = sqlify(request_dict)
    return res


@main.route('/test', methods=['POST'])
def test():
    """
    Runs given select query
    """
    request_dict = json.loads(request.data)
    res = select_query(request_dict['cmd'])
    return res


@main.route('/clear', methods=['POST'])
def clear_tab():
    """
    Qucikly clears tables
    """
    request_dict = json.loads(request.data)
    if request_dict == []:
        clear_tables()
    else:
        clear_tables(request_dict)
    declare_tables()
    return "cleared"
