
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# set the secret key.  keep this really secret: required to use session
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres://ano@localhost/vinndb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
