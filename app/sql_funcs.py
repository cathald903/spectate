"""
Functions dicating how the SQL statements are to be generated
"""
from datetime import datetime
import pytz
from .helpers import select_query, get_simple_sql_operator
from .tables import determine_tab_class

##############################
###    Simple SQL Funcs    ###
##############################


def get_sql_group(table_list: list, is_complex: bool = None):
    """
    Creating the group by clauses for an sql statement by defaulitng to grouping
    on the primary key of the table as defined in it's Class
    """
    joiner = " "
    group_by_str = ""
    if is_complex:
        table_list = [table_list[0]]
    for tab in table_list:
        tab_obj = determine_tab_class(tab)
        if is_complex:
            group_by_str += f"{joiner}{tab_obj.shorthand}.{tab_obj.pkey}"
        else:
            group_by_str += f"{joiner}{tab_obj.pkey}"
        joiner = ","
    return group_by_str


def simple_sqlify(filters: dict, joiner: str = " "):
    """
    Creating the where clauses for simple sql statements by referencing
    a predefined dictionary of  user input -> sql operator
    """
    if len(filters) == 0:
        return ""
    value = filters['val']
    if isinstance(value, str):
        value = f"'{value}'"
    elif isinstance(value, bool):
        value = 'TRUE' if value else 'FALSE'
    elif value is None:
        value = 'NULL'
    else:
        if isinstance(value, dict):
            value['date'] = datetime.strptime(
                value['date'], '%Y-%m-%dT%H:%M:%SZ')
            if not value['timezone'] == "UTC":
                tz = value['timezone']
                value = value['date']
                value.replace(tzinfo=pytz.utc)
                target_timezone = pytz.timezone(tz)
                value = value.astimezone(target_timezone)
            else:
                value = value['date']
            value = f"'{value.strftime('%Y-%m-%d %H:%M:%S')}'"
    operator = get_simple_sql_operator(filters['operation'])
    where = f"""{joiner}{filters['filler_col']} {operator} {value}"""
    return where


def get_simple_sqlify_aggregate(aggregate: list, joiner: str, col_str: str, is_complex: bool = None):
    """
    Creating the having clauses for sql statements by referencing
    a predefined dictionary of  user input -> sql aggreagators
    """
    if len(aggregate) == 0:
        return ["", col_str]
    sql_aggregators = {
        "count": "COUNT",
        "sum": "SUM",
        "avg": "AVG",
        "min": "MIN",
        "max": "MAX"
    }
    if is_complex:
        agg_col_name = f"{aggregate['agg_operation']}_{aggregate['agg_col'].split('.')[1]}"
    else:
        agg_col_name = f"{aggregate['agg_operation']}_{aggregate['agg_col']}"
    col_str += f""",{sql_aggregators[aggregate['agg_operation']]}({aggregate['agg_col']})
      as {agg_col_name}"""
    value = aggregate['val']
    if isinstance(value, str):
        value = f"'{value}'"
    elif isinstance(value, bool):
        value = 'TRUE' if value else 'FALSE'
    elif value is None:
        value = 'NULL'
    agg_str = f"""{joiner}{agg_col_name}
            {get_simple_sql_operator(aggregate['operation'])} {value}"""
    return [agg_str, col_str]

##############################
###    Complex SQL Funcs   ###
##############################


def get_complex_columns(table_list: list, column_list: list):
    """
    Creating joined column names by appending the shorthand table name
    found in the Class eg Sport = s
    """
    column_string = []
    for tab, columns in zip(table_list, column_list):
        columns = columns.split(",")
        shorthand = (determine_tab_class(tab)).shorthand
        for col in columns:
            if len(col):
                column_string.append(f"{shorthand}.{col}")
    return ",".join(column_string)


def get_complex_joins(table_list: list, lead_tab: str, tab_obj: object):
    """
    Determining the joins for the tables based on the joins necessary,
    eg if the given input is sports and selection, then event also needs to be joined on
    Joins are predefined in the table's Class for each of the other tables
    """
    if lead_tab == "Sport" and "Selection" in table_list:
        return f""" {tab_obj.link_to['Selection']} """
    elif lead_tab == "Selection" and "Sport" in table_list:
        return f""" {tab_obj.link_to['Sport']} """
    else:
        join_list = []
        for tab in table_list:
            join_list.append(f""" {tab_obj.link_to[tab]} """)
        return ",".join(join_list)


def get_complex_from(table_list: list):
    """
    Generates the shorthand of the table as decided by it's class, eg Sport as s or Event as e
    """
    lead_tab = table_list[0]
    tab_obj = determine_tab_class(lead_tab)
    additional_joins = get_complex_joins(table_list[1:], lead_tab, tab_obj)
    from_str = f"""from {lead_tab} as {tab_obj.shorthand} {additional_joins}"""
    return from_str


def get_complex_where(table_list: list, filters_list: list):
    """
    Appends the tables shorthand, eg Sport as s, to the given filter in the case where we have joins
    """
    where_str = ""
    joiner = " "
    for tab, filters in zip(table_list, filters_list):
        tab_obj = determine_tab_class(tab)
        for fil in filters:
            if len(fil):
                fil['filler_col'] = f"{tab_obj.shorthand}.{fil['filler_col']}"
                where_str += simple_sqlify(fil, joiner)
                joiner = " AND "
    return where_str


def get_complex_agg(table_list: list, agg_list, col_str: str):
    """
    Appends the tables shorthand(Sport as s) to the given aggreagte in the case where we have joins
    """
    agg_str = ""
    joiner = " "
    for tab, aggregates in zip(table_list, agg_list):
        for aggregate in aggregates:
            if len(aggregate):
                tab_obj = determine_tab_class(tab)
                aggregate['agg_col'] = f"{tab_obj.shorthand}.{aggregate['agg_col']}"
                ag_string, col_str = get_simple_sqlify_aggregate(
                    aggregate, joiner, col_str, True)
                agg_str += ag_string
                joiner = " AND "
    return [agg_str, col_str]


def complex_sqlify(filters: dict):
    """
    Generates the different part of the SQL statement depending on the columns,
    filters, tables and aggreagates specified
    """
    col_str = get_complex_columns(filters['table'], filters['select_columns'])
    filter_str = get_complex_from(filters['table'])
    where_str = get_complex_where(filters['table'], filters['filters'])
    if len(where_str) > 0:
        where_str = f"""WHERE
        {where_str}       
    """
    else:
        where_str = ""
    group_by = f"""GROUP BY {get_sql_group(filters['table'],True)}"""
    agg_str, col_str = get_complex_agg(
        filters['table'], filters['aggregate'], col_str)
    agg_str = f"""HAVING {agg_str}"""
    cmd = f""" Select
        {col_str}
        {filter_str}
        {where_str}
        {group_by}
        {agg_str}"""
    return select_query(cmd)


def sqlify(request_dict: dict):
    """
    Sends requests that involve joins to complex_sqlify and handles one table requests
    by itself by generating the different part of the SQL statement depending on the columns,
    filters, tables and aggreagates specified
    """
    if isinstance(request_dict['table'], list):
        return complex_sqlify(request_dict)
    else:
        col_str = request_dict['select_columns']
        from_str = request_dict['table']
        base_str = ""
        joiner = " "
        for filters in request_dict['filters']:
            base_str += simple_sqlify(filters, joiner)
            joiner = " AND "
        if len(base_str) > 0:
            where_str = f""" WHERE {base_str}"""
        else:
            where_str = ""
        group_by = ""
        if 'aggregate' in request_dict.keys():
            group_by = f"""GROUP BY {get_sql_group([request_dict['table']])}"""
            joiner = " "
            for aggregate in request_dict['aggregate']:
                agg_str, col_str = get_simple_sqlify_aggregate(
                    aggregate, joiner, col_str)
                joiner = " AND "
                agg_str = f""" HAVING {agg_str}"""
        else:
            agg_str = ""
        cmd = f"""Select {col_str} from {from_str} {where_str} {group_by} {agg_str}"""
        return select_query(cmd)
