import os

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Operations:
    RESET_PASSWORD = 'reset-password'
    CHANGE_EMAIL = 'change-email'
    CONFIRM = 'confirm'


class BaseConfig(object):
    DEBUG_TB_INTERCEPT_REDIRECTS = False

    MAX_CONTENT_LENGTH = 10 * 1024 * 1024

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True

    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = 465
    MAIL_USE_SSL = True
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = ('Admin', MAIL_USERNAME)

    PROJECT_ADMIN_EMAIL = os.getenv('PROJECT_ADMIN', MAIL_USERNAME)
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', MAIL_USERNAME)

    DEFAULT_PASSWORD = os.getenv('DEFAULT_PASSWORD')

    USERS_PER_PAGE = 20

    MAIL_SUBJECT_PREFIX = '[泰科论坛]'

    UPLOADS_DEFAULT_DEST = os.path.join(basedir, 'uploads')
    UPLOAD_PATH = os.path.join(UPLOADS_DEFAULT_DEST, 'files')
    TECON_PATH = os.path.join(UPLOADS_DEFAULT_DEST, 'tecon')

    AVATARS_SAVE_PATH = os.path.join(UPLOADS_DEFAULT_DEST, 'avatars')
    AVATARS_SIZE_TUPLE = (30, 60, 150)

    PHOTO_SIZE = {'small': 300, 'medium':750}
    PHOTO_SUFFIX = {PHOTO_SIZE['small']: '_s',
                    PHOTO_SIZE['medium']: ''}  # thumbnail

    SECRET_KEY = os.getenv('SECRET_KEY', 'secret string')

    BOOTSTRAP_SERVE_LOCAL = True

    POST_PER_PAGE = 10
    TOPIC_PER_PAGE = 10
    NOTIFICATION_PER_PAGE = 30
    MAX_REPORT_TIME = os.getenv('MAX_REPORT_TIME')
    SEARCH_RESULT_PER_PAGE = 18
    NEWS_PER_PAGE = 9
    MANAGE_NEWS_PER_PAGE = 20

    WHOOSHEE_MIN_STRING_LEN = 2  #搜索限制字符设定

    CKEDITOR_FILE_UPLOADER = 'main.upload'
    CKEDITOR_ENABLE_CSRF = True

    DROPZONE_ENABLE_CSRF = True
    DROPZONE_INVALID_FILE_TYPE = '文件类型不符合规定'
    DROPZONE_FILE_TOO_BIG = '上传的文件太大：{{filesize}}M;最大：{{maxFilesize}}M.'
    DROPZONE_SERVER_ERROR = '服务器端错误：{{statusCode}}'
    DROPZONE_MAX_FILE_EXCEED = '超出最大上传数量'
    DROPZONE_MAX_FILE_SIZE = 10
    DROPZONE_DEFAULT_MESSAGE = '点击或将文件拖曳到此区域来上传文件'
    DROPZONE_ALLOWED_FILE_CUSTOM = True
    DROPZONE_ALLOWED_FILE_TYPE = 'text/*, image/*, audio/*, video/*, application/*, .rar, .log'


class DevelopmentConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'data-dev.db')


class TestingConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'      # in-memory database


class ProductionConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///' + os.path.join(basedir, 'data.db'))


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig
}

