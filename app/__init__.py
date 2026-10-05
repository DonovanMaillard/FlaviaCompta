from flask import Flask

from .components.legacy_routes import app
from .components.routes.utils import login_manager
from .components import init_db

# Connect sqlalchemy to app
init_db.db.init_app(app)


login_manager.init_app(app)