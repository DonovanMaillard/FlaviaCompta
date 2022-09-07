#! /usr/bin/env python
from app import app
from app.components.init_db import db
#from flask_bootstrap import Bootstrap


if __name__ == "__main__":
    db.init_app(app)
    #Bootstrap(app)
    app.run(debug=app.config['DEBUG'], port=app.config['APP_PORT'])