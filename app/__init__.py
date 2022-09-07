from flask import Flask

from .components.routes import app
from .components import init_db

# Connect sqlalchemy to app
init_db.db.init_app(app)