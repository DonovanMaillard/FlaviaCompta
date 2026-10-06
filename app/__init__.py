from flask import Flask

from .components.legacy_routes import app
from .components.routes.utils import login_manager, format_datetime
from .components import init_db

# Connect sqlalchemy to app
init_db.db.init_app(app)

# Init login Manager
login_manager.init_app(app)

# format_datetime filter
app.add_template_filter(format_datetime, 'format_datetime')