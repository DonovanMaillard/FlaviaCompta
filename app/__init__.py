from flask import Flask

from .components.legacy_routes import app
from .components import init_db

# Connect sqlalchemy to app
init_db.db.init_app(app)