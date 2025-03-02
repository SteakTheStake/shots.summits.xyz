# routes/__init__.py
from flask import Blueprint

main_bp = Blueprint('main_bp', __name__)
admin_bp = Blueprint('admin_bp', __name__, url_prefix='/admin')
mod_bp = Blueprint('mod_bp', __name__, url_prefix='/mod')
user_bp = Blueprint('user_bp', __name__, url_prefix='/user')

# Import the route modules so they register with the Blueprints
from . import main_routes, admin_routes, mod_routes, user_routes
