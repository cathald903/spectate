from flask import Flask,request,jsonify
from flask_sqlalchemy import SQLAlchemy
import pymysql
import yaml
import json
from datetime import datetime,timezone
import re
import urllib.parse

app = Flask(__name__)
db = yaml.full_load(open('db.yml'))
connection_str='mysql://'+db['mysql_user']+':'+db['mysql_password']+'@'+db['mysql_host']+'/'+db['mysql_db']
app.config['SQLALCHEMY_DATABASE_URI'] = connection_str
db= SQLAlchemy(app)

class Sport(db.Model):
    Name = db.Column(db.String(100),primary_key = True)
    Slug = db.Column(db.String(100),nullable= False)
    Active = db.Column(db.Boolean,nullable= False)

    def __init__(self,d:dict):
        self.Name = d['Name']
        self.Slug = url_friendly_version(d['Name'])
        self.Active = d['Active']

    def sanity_checks(self,keyvalue):
        status = []
        for key,value in keyvalue.items():
            if key == 'Active' and not type(True) == type(value):
                    status.append('Active field is not a boolean') 
        return status

    def update_values(self,keyvalue):
        if len(self.sanity_checks(keyvalue)) > 0:
            raise RuntimeError("update failed sanity checks")
        for key, value in keyvalue.items():
            setattr(self, key, value)    
    
    def __repr__(self):
        return f"[{self.Name},{self.Slug},{self.Active}]"
         
class Event(db.Model):
    Name = db.Column(db.String(100),primary_key = True)
    Slug = db.Column(db.String(100),nullable= False)
    Active = db.Column(db.Boolean,nullable= False)
    Type =  db.Column(db.String(100),nullable= False)
    Sport =  db.Column(db.String(100),nullable= False)
    Status =  db.Column(db.String(100),nullable= False)
    Scheduled_start = db.Column(db.DateTime,nullable= False)
    Actual_start = db.Column(db.DateTime,nullable= True)

    def __init__(self,d:dict):
        self.Name = d['Name']
        self.Slug = url_friendly_version(d['Name'])
        self.Active = d['Active']
        self.Type =  d['Type']
        self.Sport =  d['sport']
        self.Status =  d['status']
        self.Scheduled_start = datetime.strptime( d['Scheduled_start'], '%Y-%m-%dT%H:%M:%SZ')
        if self.status == ['Started']:
            self.Actual_start = datetime.now(timezone.utc)
    
    def sanity_checks(self,keyvalue):
        status=[]
        for key,value in keyvalue.items():
            if key == 'Name':
                status.append(True) #no restrictions on name
            elif key == 'Active':
                status.append(type(True) == type(value))
            elif key == 'Type':
                status.append(value in ['preplay','inplay'])
            elif key == 'Sport':
                status.append(value in db.session.execute(db.select(Sport).filter_by(name=value)).scalar_one())
            elif key == 'Status':
                status.append(value in ['Pending','Started','Ended','Cancelled'])
            elif key == 'Scheduled_start':
                status.append(type( datetime.now(timezone.utc)) == type(value))
        return status

    def update_values(self,keyvalue):
        for key, value in keyvalue.items():
            if key == 'Scheduled start':
                value = datetime.strptime( value, '%Y-%m-%dT%H:%M:%SZ')
                setattr(self, 'Scheduled_start', value)
                continue
            elif key == 'Status' and value == 'Started' and self.Status != 'Started':
                setattr(self, 'Actual_start', datetime.now(timezone.utc))
            setattr(self, key, value)

    def __repr__(self):
        return f"[{self.Name},{self.Slug},{self.Active},{self.Type},{self.Sport},{self.Status},{self.Scheduled_start},{self.Actual_start}]"
    
class Selection(db.Model):
    Name = db.Column(db.String(100),primary_key = True)
    Event = db.Column(db.String(100),nullable= False)
    Price =  db.Column(db.Float,nullable= False)
    Active = db.Column(db.Boolean,nullable= False)
    Outcome =  db.Column(db.String(100),nullable= False)

    def __init__(self,d:dict):
        self.Name = d['Name']
        self.Event = d['Event']
        self.Price = d['Price']
        self.Active =  d['Active']
        self.Outcome =  d['Outcome']
    
    def update_values(self,keyvalue):
        for key, value in keyvalue.items():
            setattr(self, key, value)

    def __repr__(self):
        return f"[{self.Name},{self.Event},{self.Price},{self.Active},{self.Outcome}]"
    
def url_friendly_version(name):
    sanitized = re.sub(r'[^\w\s-]', '', name)
    hyphenated = re.sub(r'[\s_]+', '-', sanitized)
    lowercased = hyphenated.lower()
    url_friendly = urllib.parse.quote(lowercased)
    return url_friendly

with app.app_context():
    db.create_all()

@app.route('/')
def homepage():
    display = f"""
    Sports: {str(Sport.query.all())}
    Events: {str(Event.query.all())}
    Selection: {str(Selection.query.all())}
    """
    return  str(display)

@app.route('/init_db')
def init_db():
    with app.app_context():
        db.create_all()
    return "Database Initalised"

@app.route('/query_sports')
def query_sports():
    print(Sport.query.all())
    return str(Sport.query.all())

@app.route('/modify_object',methods =['POST'])
def modify_object():
    d = json.loads(request.data)
    if d['object'] in ['Sport','Event','Selection']:
        obj = eval(d['object'])
    else:
        return "Invalid object type: "+ d['object']
    try:
        with app.app_context():
            if not d['kind'] in ['create','update','delete']:
                return "Invalid operation type: "+d['kind']
            if d['kind'] == 'create':
                s = obj(d)
                db.session.add(s)
            elif d['kind'] == 'update':
                s = db.session.execute(db.select(obj).filter_by(name=d['name'])).scalar_one()
                s.update_values(d)
            else:
                s = db.session.execute(db.select(obj).filter_by(name=d['name'])).scalar_one()
                db.session.delete(s)    
            db.session.commit()        
    except RuntimeError as e:
        print(e)
        return str(e)

    return d['name'] +": Updated"

if __name__ == "__main__":
    print("hello")
