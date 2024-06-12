"""
    Functions that Modify the DB
"""
from .helpers import execute_query, select_query
##############################
###            ###
##############################


def insert_cmd(table: str, obj: object, data: dict):
    """
    Inserts given data into given table
    """
    cmd = f"""
            Insert into {table}
            ({','.join(obj.columns_names)})
            values
            ({','.join(obj.columns_as_params)})
            """
    return execute_query(cmd, data)


def update_cmd(table: str, data: dict):
    """
    Updates given row in given table
    """
    cmd = f"""
            UPDATE {table}
            SET {set_statement(data)}
            WHERE Name = '{data['Name']}'
            """
    return execute_query(cmd, data)


def delete_cmd(table: str, data: dict):
    """
    Deletes given row from given table
    """
    cmd = f"""
            Delete from {table}
            WHERE Name = '{data['Name']}'
            """
    return execute_query(cmd, data)


def set_statement(update_dict: dict):
    """
    Generates set statement for use with the update clause by 
    deriving it from the given update dict
    """
    set_state = []
    for column in update_dict.keys():
        set_state.append(f"{column} = :{column}")
    return ', '.join(set_state)


def inactive_check(tab: str, update_dict: dict):
    """
    Checks to see if all Events for a Sport or all Selections for an Event are inactive
    and if they are set the Sport/Event to inactive also
    """
    if 'Event' == tab:
        check_column = 'Sport'
    else:
        check_column = 'Event'
    cmd = f"""
        Select Active from {tab}
        where {check_column} = '{update_dict[check_column]}'
        AND Active = TRUE"""
    res = select_query(cmd)
    if len(res) >= 1:
        return None
    cmd = update_cmd(
        check_column, {'Name': update_dict[check_column], 'Active': False})
    if not cmd:
        return f"Failed to set {check_column} to Inactive"

    if 'Selection' == tab:
        res = select_query(
            f"Select Sport from Event where Name = '{update_dict[check_column]}'")[0]
        inactive_check('Event', {'Sport': res[0]})
    return None
