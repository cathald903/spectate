from flask import Flask,request,jsonify
from sqlalchemy import create_engine, text
import pymysql
import pytz
import yaml
import json
from datetime import datetime,timezone
import re
import urllib.parse


app = Flask(__name__)
db = yaml.full_load(open('db.yml'))
connection_str='mysql://'+db['mysql_user']+':'+db['mysql_password']+'@'+db['mysql_host']+'/'+db['mysql_db']
db = create_engine(connection_str)

##############################
###     Helper Funcs       ###
##############################
def execute_query(cmd:str,params=None):
    with db.connect() as connection:
        conn = connection.begin()
        try:
            if params:
                res = connection.execute(text(cmd), params)
            else:
                res = connection.execute(text(cmd))
            conn.commit()  # Commit if success
            return res
        except Exception as e:
            print(e)
            conn.rollback()  # Roll back if error
            return e

def select_query(cmd:str,params=None):
    with db.connect() as connection:
        conn = connection.begin()
        try:
            if params:
                res = connection.execute(text(cmd), params).fetchall()
                res = [list(row) if len(row) else [] for row in res ]
            else:
                res = connection.execute(text(cmd)).fetchall()
                res = [list(row) if len(row) else [] for row in res ]
            conn.commit()  # Commit if success
            return res
        except Exception as e:
            print(e)
            conn.rollback()  # Roll back if error
            return e

def url_friendly_version(name):
    sanitized = re.sub(r'[^\w\s-]', '', name)
    hyphenated = re.sub(r'[\s_]+', '-', sanitized)
    lowercased = hyphenated.lower()
    url_friendly = urllib.parse.quote(lowercased)
    return url_friendly

def determine_tab_class(tab):
    if tab == "Event":
        return Events
    elif tab == "Sport":
        return Sport
    elif tab == "Selection":
        return Selection

def get_simple_sql_operator(operator):
    simple_operators = {
        "equal": "=",
        "not_equal": "!=",
        "less_than": "<",
        "greater_than": ">",
        "lequal": "<=",
        "gequal": ">="
    }
    return simple_operators[operator]
##############################
###     Modify Funcs       ###
##############################
def insert_cmd(table,obj,d):
    cmd = f"""
            Insert into {table}
            ({','.join(obj.columns_names)})
            values
            ({','.join(obj.columns_as_params)})
            """
    try:
        execute_query(cmd,d)
        return True
    except:
        return False
    
def update_cmd(table,d):
    cmd = f"""
            UPDATE {table}
            SET {set_statement(d)}
            WHERE Name = '{d['Name']}'
            """
    try:
        execute_query(cmd,d)
        return True
    except:
        return False

def delete_cmd(table,d):
    cmd = f"""
            Delete from {table}
            WHERE Name = '{d['Name']}'
            """
    try:
        execute_query(cmd,d)
        return True
    except RuntimeError as e:
        print(e)
        return False

def set_statement(update_dict):
    set_state = []
    for column in update_dict.keys():
        set_state.append(f"{column} = :{column}")
    return ', '.join(set_state)

def inactive_check(tab,update_dict):
    if 'Event' == tab:
        check_column = 'Sport'
    else:
        check_column = 'Event'
    cmd = f"""Select Active from {tab} where {check_column} = '{update_dict[check_column]}' AND Active = TRUE"""
    res = select_query(cmd)
    print(len(res))
    if len(res):
        return
    cmd=update_cmd('Sport',{'Name':update_dict[check_column],'Active':False})
    return None

##############################
###     Sanity Funcs       ###
##############################
def trim_dict(obj,update_dict):
    trimmed = {}
    for key in update_dict.keys():
        if key in obj.columns_names:
            trimmed[key]=update_dict[key]
    if 'Name' in trimmed.keys() and 'Slug' in obj.columns_names:
            trimmed['Slug'] = url_friendly_version(trimmed['Name'])
    return trimmed    

def parse_dict(obj,update_dict):
    update_dict = obj.add_missing_keys(update_dict)
    status = obj.sanity_checks(update_dict)
    if len(status) > 0:
            raise RuntimeError(status)
    update_dict = obj.additional_manips(update_dict)
    return trim_dict(obj,update_dict)



##############################
###    Simple SQL Funcs    ###
##############################
def get_sql_group(table_list,complex=None):
    joiner = " "
    group_by_str = ""
    for tab in table_list:
        print(tab)
        tab_obj = determine_tab_class(tab)
        if complex:
            group_by_str+=f"{joiner}{tab_obj.shorthand}.{tab_obj.pkey}"
        else:
            group_by_str+=f"{joiner}{tab_obj.pkey}" 
        joiner = ","
    return group_by_str

def simple_sqlify(filters,joiner = " "):
    value = filters['val']
    if isinstance(value, str):
        value = f"'{value}'"
    elif isinstance(value, bool):
        value = 'TRUE' if value else 'FALSE'
    elif value is None:
        value = 'NULL'
    else:
        if type({}) == type(value):
            value['date'] = datetime.strptime( value['date'], '%Y-%m-%dT%H:%M:%SZ')
            if not value['timezone'] == "UTC":
                tz = value['timezone']
                value = value['date']
                value.replace(tzinfo=pytz.utc)
                target_timezone = pytz.timezone(tz)
                value = value.astimezone(target_timezone)
            else:
                value = value['date']
            value = f"'{value.strftime('%Y-%m-%d %H:%M:%S')}'"
    where = f"""{joiner}{filters['filler_col']} {get_simple_sql_operator(filters['operation'])} {value}"""
    return where

def get_simple_sqlify_aggregate(aggregate,joiner,col_str,complex=None):
    sql_aggregators = {
    "count": "COUNT",
    "sum": "SUM",
    "avg": "AVG",
    "min": "MIN",
    "max": "MAX"
    }
    if complex:
        agg_col_name=f"{aggregate['agg_operation']}_{aggregate['agg_col'].split('.')[1]}"
    else:
        agg_col_name=f"{aggregate['agg_operation']}_{aggregate['agg_col']}"
    col_str += f",{sql_aggregators[aggregate['agg_operation']]}({aggregate['agg_col']}) as {agg_col_name}"
    value = aggregate['val']
    if isinstance(value, str):
        value = f"'{value}'"
    elif isinstance(value, bool):
        value = 'TRUE' if value else 'FALSE'
    elif value is None:
        value = 'NULL'
    agg_str = f"""{joiner}{agg_col_name} {get_simple_sql_operator(aggregate['operation'])} {value}"""
    return [agg_str,col_str]

##############################
###    Complex SQL Funcs   ###
##############################
def get_complex_columns(table_list,column_list):
    column_string = []
    for tab,columns in zip(table_list,column_list):
        columns = columns.split(",")
        shorthand = (determine_tab_class(tab)).shorthand
        for col in columns:
            if len(col):
                column_string.append(f"{shorthand}.{col}")
    return ",".join(column_string)

def get_complex_joins(table_list,lead_tab,tab_obj):
    if lead_tab == "Sport" and "Selection" in table_list:
        return f""" {tab_obj.link_to['Selection']} """
    elif lead_tab == "Selection" and "Sport" in table_list:
        return f""" {tab_obj.link_to['Sport']} """
    else:
        join_list = []
        for tab in table_list:
            join_list.append(f""" {tab_obj.link_to[tab]} """)
        return ",".join(join_list)

def get_complex_from(table_list):
    lead_tab = table_list[0]
    tab_obj = determine_tab_class(lead_tab)
    from_str = f"""from {lead_tab} as {tab_obj.shorthand} {get_complex_joins(table_list[1:],lead_tab,tab_obj)}"""
    return from_str

def get_complex_where(table_list,filters_list):
    where_str=""
    joiner = " "
    for tab,filters in zip(table_list,filters_list):
        tab_obj = determine_tab_class(tab)
        for fil in filters:
            if len(fil):
                fil['filler_col']=f"{tab_obj.shorthand}.{fil['filler_col']}"
                where_str+=simple_sqlify(fil,joiner)
                joiner= " AND "
    return where_str

def get_complex_agg(table_list,agg_list,col_str):
    agg_str = ""
    joiner = " "
    for tab,aggregates in zip(table_list,agg_list):
        for aggregate in aggregates:
            if len(aggregate):
                tab_obj = determine_tab_class(tab)
                aggregate['agg_col']=f"{tab_obj.shorthand}.{aggregate['agg_col']}"
                ag_string,col_str = get_simple_sqlify_aggregate(aggregate,joiner,col_str,True)
                agg_str+=ag_string
                joiner= " AND "
    return [agg_str,col_str]

def complex_sqlify(filters):
    col_str = get_complex_columns(filters['table'],filters['select_columns']) 
    filter_str = get_complex_from(filters['table'])
    where_str =f"""WHERE
        {get_complex_where(filters['table'],filters['filters'])}
    """
    group_by = f"""GROUP BY {get_sql_group(filters['table'],True)}"""
    agg_str,col_str = get_complex_agg(filters['table'],filters['aggregate'],col_str)
    agg_str = f"""HAVING {agg_str}"""
    cmd = f""" Select
        {col_str}
        {filter_str}
        {where_str}
        {group_by}
        {agg_str}"""
    print(cmd)
    return select_query(cmd)

def sqlify(request_dict):
    if type(request_dict['table']) == type([]):
        return complex_sqlify(request_dict)
    else:
        col_str = request_dict['select_columns']
        from_str = request_dict['table']
        base_str = ""
        joiner = " "
        for filters in request_dict['filters']:
            base_str+=simple_sqlify(filters,joiner)
            joiner= " AND "
        where_str = f""" WHERE {base_str}"""
        if 'aggregate' in request_dict.keys():
            group_by = f"""GROUP BY {get_sql_group([request_dict['table']])}"""
            joiner = " "
            for aggregate in request_dict['aggregate']:
                agg_str,col_str = get_simple_sqlify_aggregate(aggregate,joiner,col_str)
                joiner= " AND "
                agg_str=f""" HAVING {agg_str}"""
        else:
            agg_str = ""
        cmd = f"""Select {col_str} from {from_str} {where_str} {group_by} {agg_str}"""
        return select_query(cmd)
##########################################
###         Table Declartions          ###
##########################################
cmd = """
CREATE TABLE IF NOT EXISTS Sport (
    Name VARCHAR(75)  PRIMARY KEY,
    Slug VARCHAR(75) NOT NULL,
    Active BOOLEAN NOT NULL
);
"""
execute_query(cmd)

cmd = """
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
"""
execute_query(cmd)

cmd = """
CREATE TABLE IF NOT EXISTS Selection (
    Name VARCHAR(75)  PRIMARY KEY,
    Event VARCHAR(75) NOT NULL,
    Price FLOAT NOT NULL,
    Active BOOLEAN NOT NULL,
    Outcome VARCHAR(75),
    FOREIGN KEY (Event) REFERENCES Event(Name)
);
"""
execute_query(cmd)

##############################
###     Class Funcs        ###
##############################
class Sport():
    shorthand = "s"
    link_to = {"Event":f"join Event e ON  {shorthand}.Name=e.Sport","Selection":f"join Event e ON  {shorthand}.Name=e.Sport,join Selection se ON  e.Name=se.Event "}
    pkey = 'Name'

    def __init__(self,d:dict):
        columns_names = execute_query("DESCRIBE Sport").fetchall()
        self.columns_names = [column[0] for column in columns_names]
        self.columns_as_params = [":"+column[0] for column in columns_names]
        #d = parse_dict(self,d)
        #self.update_values(d)

    def sanity_checks(self,keyvalue:dict):
        status = []
        for key,value in keyvalue.items():
            if key == 'Active' and not type(True) == type(value):
                    status.append('Active field is not a boolean') 
        return status

    #def update_values(self,keyvalue:dict):
    #    for key, value in keyvalue.items():
    #        setattr(self, key, value)               
    
    def add_missing_keys(self,update_dict):
        return update_dict
    
    def additional_manips(self,update_dict):
        return update_dict
    
    def __repr__(self):
        return f"[{self.Name},{self.Slug},{self.Active}]"

class Events():
    shorthand = "e"
    link_to = {"Sport":f"join Sport s ON  {shorthand}.Sport=s.Name","Selection":f"join Selection se ON {shorthand}.Name=se.Event"}
    pkey = 'Name'

    def __init__(self,d:dict):
        columns_names = execute_query("DESCRIBE Event").fetchall()
        self.columns_names = [column[0] for column in columns_names]
        self.columns_as_params = [":"+column[0] for column in columns_names]
        #d = parse_dict(self,d)
        #self.update_values(d)
    
    def sanity_checks(self,keyvalue:dict):
        status=[]
        for key,value in keyvalue.items():
            if key == 'Active' and not type(True) == type(value):
                status.append('Active field is not a boolean')
            elif key == 'Type' and not value in ['preplay','inplay']:
                status.append('Invalid "Type" field: ' + value)
            elif key == 'Sport':
                existing_sport = execute_query(f"Select * from Sport where Name = '{value}'").fetchall()
                if not len(existing_sport):
                    print(existing_sport)
                    status.append('Unknown Sport:' + value)
            elif key == 'Status' and not value in ['Pending','Started','Ended','Cancelled']:
                status.append('Invalid "Status" field: ' + value)
            elif key == 'Scheduled_start':
                try:
                    datetime.strptime( value, '%Y-%m-%dT%H:%M:%SZ')
                except:
                    status.append('Not a valid UTC datetime:' + value)                
        return status

    #def update_values(self,keyvalue:dict):
    #    for key, value in keyvalue.items():
    #        setattr(self, key, value)

    def add_missing_keys(self,update_dict):
        update_dict['Scheduled_start']=update_dict['Scheduled start']
        update_dict['Actual_start']=None
        return update_dict

    def additional_manips(self,update_dict):
        update_dict['Scheduled_start']=update_dict['Scheduled_start'][:-1]
        if not update_dict['Status'] == 'Started':
            update_dict['Actual_start']=None
            return update_dict
        if 'create' == update_dict['kind']:
            t = datetime.now(timezone.utc)
            update_dict['Actual_start']=t.strftime('%Y-%m-%d %H:%M:%S')
        else:
            cmd = f"Select Status from Event where Name = '{update_dict['Name']}'"
            status =execute_query(cmd).fetchone()[0]
            if 'Pending'== status:
                t = datetime.now(timezone.utc)
                update_dict['Actual_start']=t.strftime('%Y-%m-%d %H:%M:%S')
        return update_dict      

    def __repr__(self):
        return f"[{self.Name},{self.Slug},{self.Active},{self.Type},{self.Sport},{self.Status},{self.Scheduled_start},{self.Actual_start}]"

class Selection():
    shorthand = "se"
    link_to = {"Event":f"join Event e ON  {shorthand}.Event=e.Name","Sport":f"join Event e ON {shorthand}.Event=e.Name,join Sport s ON  e.Event=s.Name "}
    pkey = 'Name'

    def __init__(self,d:dict):
        columns_names = execute_query("DESCRIBE Selection").fetchall()
        self.columns_names = [column[0] for column in columns_names]
        self.columns_as_params = [":"+column[0] for column in columns_names]
        #d = parse_dict(self,d)
        #self.update_values(d)
    
    def sanity_checks(self,keyvalue):
        status=[]
        for key,value in keyvalue.items():
            if key == 'Event':
                existing_event = execute_query(f"Select * from Event where Name = '{value}'").fetchall()
                if not len(existing_event):
                    status.append('Unknown Event:' + value)
            elif key == 'Price' and not type(0.2) == type(value):
                status.append('Price field is not a float')
            elif key == 'Active' and not type(True) == type(value):
                status.append('Active field is not a boolean')
            elif key == 'Outcome' and not value in ['Unsettled','Void','Lose','Win']:
                status.append('Outcome field is not valid: ' + value)                
        return status
    
    #def update_values(self,keyvalue):
    #    for key, value in keyvalue.items():
    #        setattr(self, key, value)  

    def add_missing_keys(self,update_dict):
        return update_dict
    
    def additional_manips(self,update_dict):
        update_dict['Price'] =round(update_dict['Price'],2)
        return update_dict

    def __repr__(self):
        return f"[{self.Name},{self.Event},{self.Price},{self.Active},{self.Outcome}]"
    
##############################
###     Routes             ###
##############################
@app.route('/')
def homepage():
    res = []
    for obj in ['Sport','Event','Selection']:
        cmd = f"Select * from {obj}"
        r = select_query(cmd)
        res.append(f"{obj}s:")
        res.append(r)
    return res


@app.route('/modify_object',methods =['POST'])
def modify_object():
    request_dict = json.loads(request.data)
    if not request_dict['object'] in ['Sport','Event','Selection'] or not request_dict['kind'] in ['create','update','delete']:
        return "Invalid 'object' and/or 'kind' value "
    
    table,kind = [request_dict['object'],request_dict['kind']]
    obj = determine_tab_class(table)
    obj = obj(request_dict)
    update_dict = parse_dict(obj,request_dict)
    try:
        if kind == 'create':
            res = insert_cmd(table,obj,update_dict)
        elif kind == 'update':
            res = update_cmd(table,update_dict)  
        else:
            res = delete_cmd(table,update_dict) 
    except RuntimeError as e:
        print(e)
        return str(e)
    if request_dict['object'] in ['Event','Selection']:
        try:
            inactive_check(request_dict['object'],update_dict)
        except:
            pass

    if res:
        return request_dict['Name'] +": Updated"
    else:
        return  request_dict['Name'] +": Failed to update"

@app.route('/filter_object',methods =['POST'])
def filter_object():
    request_dict = json.loads(request.data)
    res = sqlify(request_dict)
    return res

@app.route('/test',methods =['POST'])
def test():    
    request_dict = json.loads(request.data)
    res =select_query(request_dict['cmd'])
    return res

if __name__ == "__main__":
    print("hello")
