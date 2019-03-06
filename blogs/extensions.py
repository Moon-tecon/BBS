from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from flask_moment import Moment
from flask_login import LoginManager, AnonymousUserMixin
from flask_bootstrap import Bootstrap
from flask_migrate import Migrate
from flask_mail import Mail
from flask_avatars import Avatars
from flask_ckeditor import CKEditor
from flask_whooshee import Whooshee
from flask_dropzone import Dropzone

db = SQLAlchemy()
csrf = CSRFProtect()
moment = Moment()
login_manager = LoginManager()
bootstrap = Bootstrap()
migrate = Migrate()
mail = Mail()
avatars = Avatars()
ckeditor = CKEditor()
whooshee = Whooshee()
dropzone = Dropzone()

login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'warning'
login_manager.login_message = '请先登录'

login_manager.refresh_view = 'auth.re_authenticate'
login_manager.needs_refresh_message_category = 'warning'
login_manager.needs_refresh_message = '为了保护你的账户安全，请重新登录。'


class Guest(AnonymousUserMixin):
    @property
    def is_admin(self):
        return False

    def can(self, permission_name):
        return False


login_manager.anonymous_user = Guest
