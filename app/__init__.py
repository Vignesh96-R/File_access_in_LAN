from flask import Flask

def create_app():
    app = Flask(__name__)
    from . import routes
    routes.init_app(app)
    return app
