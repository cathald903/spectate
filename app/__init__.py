"""
init file
"""
from flask import Flask


def create_app():
    """
    Intialises the application by reading in database config and opening the connection
    """
    app = Flask(__name__)

    # get db connection
    from app.db import db

    # Init tables
    from app.tables import declare_tables
    declare_tables()

    # Register blueprints
    from app.routes import main
    app.register_blueprint(main)
    return app
