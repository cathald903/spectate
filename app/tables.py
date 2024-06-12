"""
contains the function to initalise the tables in the DB
Also contains their respective classes, which contain default info and 
defined methods for sanity checks and data manipulation
"""
from datetime import datetime, timezone
from .helpers import execute_query, select_query, url_friendly_version

##########################################
###         Table Declartions          ###
##########################################


def declare_tables():
    """
    Intialises the Sport, Event and Selection tables
    """
    commands = ["""
    CREATE TABLE IF NOT EXISTS Sport (
        Name VARCHAR(75)  PRIMARY KEY,
        Slug VARCHAR(75) NOT NULL,
        Active BOOLEAN NOT NULL
    );
    """,
                """
    CREATE TABLE IF NOT EXISTS Event (
        Name VARCHAR(75)  PRIMARY KEY,
        Slug VARCHAR(75) NOT NULL,
        Active BOOLEAN NOT NULL,
        Type VARCHAR(75) NOT NULL,
        Sport VARCHAR(75) NOT NULL,
        Status VARCHAR(75) NOT NULL,
        Scheduled_start DATETIME  NOT NULL,
        Actual_start DATETIME  NULL,
        FOREIGN KEY (Sport) REFERENCES Sport(Name)
    );
    """,
                """
    CREATE TABLE IF NOT EXISTS Selection (
        Name VARCHAR(75)  PRIMARY KEY,
        Event VARCHAR(75) NOT NULL,
        Price FLOAT NOT NULL,
        Active BOOLEAN NOT NULL,
        Outcome VARCHAR(75),
        FOREIGN KEY (Event) REFERENCES Event(Name)
    );
    """
                ]
    return [execute_query(cmd) for cmd in commands]


def clear_tables(tables: list = None):
    """
    Quick way of truncating db
    """
    def quick_cmd(tab: str):
        cmd = f"drop table {tab};"
        return cmd
    if tables is None:
        return [execute_query(quick_cmd(tab))for tab in ['Selection', 'Event', 'Sport']]
    else:
        return [execute_query(quick_cmd(tab)) for tab in [tables]]


def determine_tab_class(tab: str):
    """
    table -> Class quick reference
    """
    if tab == "Event":
        return Events
    elif tab == "Sport":
        return Sport
    elif tab == "Selection":
        return Selection
##############################
###     Class Funcs        ###
##############################


class Sport():
    """
    The Class for the Sport table, holds default information and 
    specified sanity checks and data manipulation
    """
    shorthand = "s"
    link_to = {"Event": f"join Event e ON  {shorthand}.Name=e.Sport",
               "Selection": f"""join Event e ON  
               {shorthand}.Name = e.Sport,
               join Selection se ON  e.Name = se.Event """}
    pkey = 'Name'

    def __init__(self):
        columns_names = select_query("DESCRIBE Sport")
        self.columns_names = [column[0] for column in columns_names]
        self.columns_as_params = [":"+column[0] for column in columns_names]

    def sanity_checks(self, keyvalue: dict):
        """
        No restrictions on Name, Slug is derived from Name therefore
        the only sanity check is if Active is a boolean
        """
        status = []
        for key, value in keyvalue.items():
            if key == 'Active' and not isinstance(value, bool):
                status.append('Active field is not a boolean')
        return status

    def add_missing_keys(self, update_dict: dict):
        """
        No additional keys to add
        """
        return update_dict

    def additional_manips(self, update_dict: dict):
        """
        Need to derive Slug from Name to make sure it is url friendly
        """
        update_dict['Slug'] = url_friendly_version(update_dict['Name'])
        return update_dict


class Events():
    """
    The Class for the Events table, holds default information and 
    specified sanity checks and data manipulation
    """
    shorthand = "e"
    link_to = {"Sport": f"join Sport s ON  {shorthand}.Sport=s.Name",
               "Selection": f"join Selection se ON {shorthand}.Name=se.Event"}
    pkey = 'Name'

    def __init__(self):
        columns_names = select_query("DESCRIBE Event")
        self.columns_names = [column[0] for column in columns_names]
        self.columns_as_params = [":"+column[0] for column in columns_names]

    def sanity_checks(self, keyvalue: dict):
        """
        Contains various checks of the given fields to ensure that
        they align with table declaration
        """
        status = []
        for key, value in keyvalue.items():
            if key == 'Active' and not isinstance(value, bool):
                status.append('Active field is not a boolean')
            elif key == 'Type' and not value in ['preplay', 'inplay']:
                status.append('Invalid "Type" field: ' + value)
            elif key == 'Sport':
                existing_sport = select_query(
                    f"Select * from Sport where Name = '{value}'")
                if len(existing_sport) == 0:
                    status.append('Unknown Sport:' + value)
            elif key == 'Status' and not value in ['Pending', 'Started', 'Ended', 'Cancelled']:
                status.append('Invalid "Status" field: ' + value)
            elif key == 'Scheduled_start':
                try:
                    datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ')
                except TypeError:
                    status.append('Not a valid UTC datetime:' + value)
        return status

    def add_missing_keys(self, update_dict: dict):
        """
        Need some renaming based off of specified names as we don't want
        a name like Scheduled start as a column name with it's spaces
        """
        update_dict['Scheduled_start'] = update_dict['Scheduled start']
        update_dict['Actual_start'] = None
        return update_dict

    def additional_manips(self, update_dict: dict):
        """
        Getting the Slug, putting the UTC json string into a format MYSQL likes
        and defining Actual_start when an event is starting
        """
        update_dict['Slug'] = url_friendly_version(update_dict['Name'])
        update_dict['Scheduled_start'] = update_dict['Scheduled_start'][:-1]
        if update_dict['Status'] != 'Started':
            update_dict['Actual_start'] = None
            return update_dict
        if 'create' == update_dict['kind']:
            t = datetime.now(timezone.utc)
            update_dict['Actual_start'] = t.strftime('%Y-%m-%d %H:%M:%S')
        else:
            cmd = f"Select Status from Event where Name = '{update_dict['Name']}'"
            status = select_query(cmd)[0]
            cmd = f"Select Actual_start from Event where Name = '{update_dict['Name']}'"
            time = select_query(cmd)[0][0]
            if 'Pending' in status:
                t = datetime.now(timezone.utc)
                update_dict['Actual_start'] = t.strftime('%Y-%m-%d %H:%M:%S')
            elif time is not None and 'Started' in status:
                update_dict['Actual_start'] = time
        return update_dict


class Selection():
    """
    The Class for the Selection table, holds default information and 
    specified sanity checks and data manipulation
    """
    shorthand = "se"
    link_to = {"Event": f"join Event e ON  {shorthand}.Event=e.Name",
               "Sport": f"""join Event e ON
               {shorthand}.Event = e.Name,
               join Sport s ON  e.Event = s.Name """}
    pkey = 'Name'

    def __init__(self):
        columns_names = select_query("DESCRIBE Selection")
        self.columns_names = [column[0] for column in columns_names]
        self.columns_as_params = [":"+column[0] for column in columns_names]

    def sanity_checks(self, keyvalue):
        """
        No restrictions on Name, Slug is derived from Name therefore
        the only sanity check is if Active is a boolean
        """
        status = []
        for key, value in keyvalue.items():
            if key == 'Event':
                existing_event = select_query(
                    f"Select * from Event where Name = '{value}'")
                if len(existing_event) == 0:
                    status.append('Unknown Event:' + value)
            elif key == 'Price' and not isinstance(value, float):
                status.append('Price field is not a float')
            elif key == 'Active' and not isinstance(value, bool):
                status.append('Active field is not a boolean')
            elif key == 'Outcome' and not value in ['Unsettled', 'Void', 'Lose', 'Win']:
                status.append('Outcome field is not valid: ' + value)
        return status

    def add_missing_keys(self, update_dict: dict):
        """
        No additional keys to add
        """
        return update_dict

    def additional_manips(self, update_dict: dict):
        """
        Need to round Price to 2 decimal places
        """
        update_dict['Price'] = round(update_dict['Price'], 2)
        return update_dict
