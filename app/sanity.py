"""
Contains some basic sanity check functions and parse_dict to dictate
the order of the sanity check workflow
"""


def trim_dict(obj: object, update_dict: dict):
    """
    Trims update_dict to just have the keys that are columns in the table
    """
    trimmed = {}
    for key in update_dict.keys():
        if key in obj.columns_names:
            trimmed[key] = update_dict[key]
    return trimmed


def parse_dict(obj: object, update_dict: dict):
    """
    Adds missing keys, eg Scheduled start -> Scheduled_start
    Runs the Class' defined sanity checks to ensure correct typing of columns
    Does additional manipulations as defined by the classes eg defining Actual_start 
    Trims the dictionary to only contain column keys
    """
    update_dict = obj.add_missing_keys(update_dict)
    status = obj.sanity_checks(update_dict)
    if len(status) > 0:
        raise RuntimeError(status)
    update_dict = obj.additional_manips(update_dict)
    return trim_dict(obj, update_dict)
