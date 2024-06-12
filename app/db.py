"""
Connects to the db for import into the other modules
"""
from sqlalchemy import create_engine
import yaml


def get_db():
    """
    connect to db
    """
    db_config = yaml.full_load(open('app/db.yml', encoding="utf-8"))
    base_str = "mysql+pymysql://"
    user_str = db_config['mysql_user']
    password_str = db_config['mysql_password']
    host_str = db_config['mysql_host']
    db_str = db_config['mysql_db']
    connection_str = f"{base_str}{user_str}:{password_str}@{host_str}/{db_str}"
    return create_engine(connection_str)


db = get_db()
