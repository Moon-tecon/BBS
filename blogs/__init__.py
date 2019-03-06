import os
import click
import logging
from logging.handlers import RotatingFileHandler, SMTPHandler
from flask import Flask, render_template, request
from flask_wtf.csrf import CSRFError
from flask_login import current_user

from blogs.settings import config
from blogs.extensions import db, csrf, migrate, moment, mail, bootstrap, avatars, login_manager, ckeditor, \
    whooshee, dropzone
from blogs.blueprints.main import main_bp
from blogs.blueprints.ajax import ajax_bp
from blogs.blueprints.auth import auth_bp
from blogs.blueprints.admin import admin_bp
from blogs.blueprints.user import user_bp
from blogs.blueprints.tecon import view_bp
from blogs.models.blogs import Post, File, User, Role, Topic, Notification, Status, Group
from blogs.models.tecon import Series, Item

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_CONFIG', 'development')

    app = Flask('blogs')

    app.config.from_object(config[config_name])

    app.config['WTF_I18N_ENABLED'] = False

    register_extensions(app)
    register_blueprints(app)
    register_commands(app)      #注册自定义shell命令
    register_errorhandlers(app)         #注册错误处理函数
    register_shell_context(app)   #注册shell上下文处理函数
    register_template_context(app)    #注册模板上下文处理函数
    register_logger(app)

    return app


def register_extensions(app):
    db.init_app(app)
    csrf.init_app(app)
    moment.init_app(app)
    login_manager.init_app(app)
    bootstrap.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    avatars.init_app(app)
    ckeditor.init_app(app)
    whooshee.init_app(app)
    dropzone.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)


def register_logger(app):
    class RequestFormatter(logging.Formatter):

        def format(self, record):
            record.url = request.url
            record.remote_addr = request.remote_addr
            return super(RequestFormatter, self).format(record)

    request_formatter = RequestFormatter(
        '[%(asctime)s] %(remote_addr)s requested %(url)s\n'
        '%(levelname)s in %(module)s: %(message)s'
    )

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    file_handler = RotatingFileHandler(os.path.join(basedir, 'logs/forum.log'),
                                       maxBytes=10 * 1024 * 1024, backupCount=10)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    mail_handler = SMTPHandler(
        mailhost=os.getenv('MAIL_SERVER'),
        fromaddr=os.getenv('MAIL_USERNAME'),
        toaddrs=os.getenv('PROJECT_ADMIN'),
        subject='Tecon Forum Application Error',
        credentials=(os.getenv('MAIL_USERNAME'), os.getenv('MAIL_PASSWORD')))
    mail_handler.setLevel(logging.ERROR)
    mail_handler.setFormatter(request_formatter)

    if not app.debug:
        app.logger.addHandler(mail_handler)
        app.logger.addHandler(file_handler)


def register_blueprints(app):
    app.register_blueprint(main_bp, url_prefix='/')
    app.register_blueprint(ajax_bp, url_prefix='/ajax')
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(view_bp, url_prefix='/tecon')


def register_errorhandlers(app):
    @app.errorhandler(400)
    def bad_request(e):
        return render_template('errors/400.html'), 400

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(413)
    def request_entity_too_large(e):
        return render_template('errors/413.html'), 413

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        return render_template('errors/400.html', description=e.description), 500


def register_template_context(app):
    @app.context_processor
    def make_template_context():
        if current_user.is_authenticated:
            notification_count = Notification.query.with_parent(current_user).filter_by(is_read=False).count()
        else:
            notification_count = None
        introduces = Item.query.filter_by(saved=False, series_id=1).order_by(Item.name).all()
        products = Item.query.filter_by(saved=False, series_id=2).order_by(Item.name).all()
        group3 = Group.query.get_or_404(3)
        return dict(notification_count=notification_count, introduces=introduces, products=products, group3=group3)


def register_commands(app):
    @app.cli.command()
    @click.option('--drop', is_flag=True, help='Create after drop.')
    def initdb(drop):
        """Initialize the database."""
        if drop:
            click.confirm('This operation will delete the database, do you want to continue?', abort=True)
            db.drop_all()
            click.echo('Drop tables.')
        db.create_all()
        click.echo('Initialized database.')

    @app.cli.command()
    @click.option('--password', prompt=True, hide_input=True,
                  confirmation_prompt=True, help='The password used to login.')
    def init(password):
        """Initialize Blogs."""
        click.echo('Initializing the database...')
        db.create_all()

        click.echo('Initializing the roles and permissions...')
        Role.init_role()

        click.echo('Initializing the status...')
        Status.init_status()

        click.echo('Initializing the series...')
        Series.init_series()

        admin = User.query.first()
        if admin is not None:
            click.echo('The administrator already exists, updating...')
            admin.set_password(password)
        else:
            click.echo('Creating the temporary administrator account...')
            admin = User(email=app.config['ADMIN_EMAIL'], username='admin', confirmed=True)
            admin.set_password(password)
            db.session.add(admin)

        db.session.commit()
        click.echo('Done.')

    @app.cli.command()
    @click.option('--user', default=20, help='Quantity of users, default is 20.')
    @click.option('--post', default=100, help='Quantity of posts, default is 100.')
    @click.option('--topic', default=30, help='Quantity of topics, default is 30.')
    @click.option('--group', default=5, help='Quantity of groups, default is 5.')
    @click.option('--collect', default=30, help='Quantity of collects, default is 30.')
    def forge(topic, user, post, collect, group):
        """Generate fake data."""
        from blogs.fakes import fake_admin, fake_topics, fake_users, fake_posts, fake_groups, \
            fake_collect

        db.drop_all()
        db.create_all()

        click.echo('Initializing the roles and permissions...')
        Role.init_role()

        click.echo('Initializing the status...')
        Status.init_status()

        click.echo('Initializing the series...')
        Series.init_series()

        click.echo('Generating the administrator...')
        fake_admin()

        click.echo('Generating %d users...' % user)
        fake_users(user)

        click.echo('Generating %d groups...' % group)
        fake_groups(group)

        click.echo('Generating %d topics...' % topic)
        fake_topics(topic)

        click.echo('Generating %d posts...' % post)
        fake_posts(post)

        click.echo('Generating %d collects...' % collect)
        fake_collect(collect)

        click.echo('Done')


def register_shell_context(app):
    @app.shell_context_processor
    def make_shell_context():
        return dict(db=db)
