from flask import Flask,request
from flask_sqlalchemy import SQLAlchemy
import pymysql
import yaml
import json

app = Flask(__name__)
db = yaml.full_load(open('db.yml'))
connection_str='mysql://'+db['mysql_user']+':'+db['mysql_password']+'@'+db['mysql_host']+'/'+db['mysql_db']
app.config['SQLALCHEMY_DATABASE_URI'] = connection_str
db= SQLAlchemy(app)

class sport(db.Model):
    name = db.Column(db.String(100),primary_key = True)
    slug = db.Column(db.String(100),nullable= False)
    active = db.Column(db.String(100),nullable= False)

    def __init__(self,name,slug,active):
        self.name = name
        self.slug = slug
        self.active = active
    
    def __repr__(self):
        return f"[{self.name},{self.slug},{self.active}]"
         

@app.route('/')
def hello_world():
    return connection_str

@app.route('/query_sports')
def query_sports():
    print(sport.query.all())
    return "200"

@app.route('/init_db', methods = ['GET'])
def init_db():
    with app.app_context():
        db.create_all()
    return "0"

@app.route('/add_sport', methods = ['POST'])
def example():
    d = json.loads(request.data)
    print(d)
    with app.app_context():
        s = sport(d['name'],d['slug'],'True' == d['active'])
        db.session.add(s)
        db.session.commit()
    return str(d['number'])

if __name__ == "__main__":
    print("hello")
