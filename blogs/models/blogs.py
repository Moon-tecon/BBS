from blogs.extensions import db
from datetime import datetime
import os
import time
import uuid
from flask import current_app
from flask_avatars import Identicon
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask.sessions import SessionMixin

from blogs.extensions import whooshee


# relationship table
roles_permissions = db.Table('roles_permissions',
                             db.Column('role_id', db.Integer, db.ForeignKey('role.id')),
                             db.Column('permission_id', db.Integer, db.ForeignKey('permission.id'))
                             )


class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True)
    roles = db.relationship('Role', secondary=roles_permissions, back_populates='permissions')


class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True)

    users = db.relationship('User', back_populates='role')
    permissions = db.relationship('Permission', secondary=roles_permissions, back_populates='roles')

    @staticmethod
    def init_role():
        roles_permissions_map = {
            '普通用户': ['FOLLOW', 'COLLECT', 'COMMENT', 'PUBLISH'],
            '员工': ['FOLLOW', 'COLLECT', 'COMMENT', 'PUBLISH', 'MEMBER'],
            '宣传员': ['FOLLOW', 'COLLECT', 'COMMENT', 'PUBLISH', 'MEMBER', 'PUBLICITY'],
            '协管员': ['FOLLOW', 'COLLECT', 'COMMENT', 'PUBLISH', 'MEMBER', 'PUBLICITY', 'MODERATE'],
            '管理员': ['FOLLOW', 'COLLECT', 'COMMENT', 'PUBLISH', 'MEMBER', 'PUBLICITY', 'MODERATE',
                              'ADMINISTER']
        }

        for role_name in roles_permissions_map:
            role = Role.query.filter_by(name=role_name).first()
            if role is None:
                role = Role(name=role_name)
                db.session.add(role)
            role.permissions = []
            for permission_name in roles_permissions_map[role_name]:
                permission = Permission.query.filter_by(name=permission_name).first()
                if permission is None:
                    permission = Permission(name=permission_name)
                    db.session.add(permission)
                role.permissions.append(permission)
        db.session.commit()


class Status(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True)

    groups = db.relationship('Group', back_populates='status', cascade='all')

    @staticmethod
    def init_status():
        status_list = ['仅内部','限制级', '用户开放', '游客可访问']
        #'仅内部'：仅内部员工可查看；
        #'limit'用户可查看不可编辑；'限制级'
        #'apart'用户可编辑，游客不可查看； '用户开放'
        #'all'游客可查看; '游客可访问'
        for name in status_list:
            status = Status.query.filter_by(name=name).first()
            if status is None:
                status = Status(name=name)
                db.session.add(status)
        db.session.commit()


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), nullable=False, unique=True)
    intro = db.Column(db.Text)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status_id = db.Column(db.Integer, db.ForeignKey('status.id'))

    topics = db.relationship('Topic', back_populates='group', cascade='all', lazy='dynamic')
    admin = db.relationship('User', back_populates='admin_groups')
    status = db.relationship('Status', back_populates='groups')

    def __init__(self, **kwargs):
        super(Group, self).__init__(**kwargs)

    def get_last_post(self):
        topic_id_list = []
        for topic in self.topics:
            topic_id_list.append(topic.id)
        try:
            last_post = Post.query.filter(Post.topic_id.in_(topic_id_list), Post.saved == False). \
                order_by(Post.timestamp.desc()).first()
        except:
            last_post = None
        return last_post

    def last_post_sign(self):
        sign = self.get_last_post().timestamp.strftime(format("%y%m%d%H%M%S"))
        return sign

    def get_last_topic(self):
        if self.topics:
            last_topic = Topic.query.with_parent(self).filter_by(saved=False).order_by(
                Topic.timestamp.desc()).first()
            return last_topic

    def last_topic_sign(self):
        sign = self.get_last_topic().timestamp.strftime(format("%y%m%d%H%M%S"))
        return sign

    def get_topic_count(self):
        topic_count = Topic.query.with_parent(self).filter_by(saved=False).count()
        return topic_count

    def get_post_count(self):
        topic_id_list = []
        for topic in self.topics:
            topic_id_list.append(topic.id)
        count = Post.query.filter(Post.topic_id.in_(topic_id_list), Post.saved == False).count()
        return count

    def top_topic(self):
        topics = Topic.query.with_parent(self).filter_by(saved=False, top=True).order_by(Topic.top_timestamp.desc()).all()
        return topics


# relationship object
class Collect(db.Model):
    collector_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    collected_id = db.Column(db.Integer, db.ForeignKey('topic.id'), primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    collector = db.relationship('User', back_populates='collections', lazy='joined')
    collected = db.relationship('Topic', back_populates='collectors', lazy='joined')


#relationship object
class Read(db.Model):
    reader_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    readed_id = db.Column(db.Integer, db.ForeignKey('topic.id'), primary_key=True)

    reader = db.relationship('User', back_populates='reads', lazy='joined')
    readed = db.relationship('Topic', back_populates='readers', lazy='joined')


#relationship object
class Notice(db.Model):
    noticed_id = db.Column(db.Integer, db.ForeignKey('topic.id'), primary_key=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    noticed = db.relationship('Topic', back_populates='receivers', lazy='joined')
    receiver = db.relationship('User', back_populates='notices', lazy='joined')


@whooshee.register_model('name', 'body')
class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), nullable=False)
    body = db.Column(db.Text, nullable=False)
    read_time = db.Column(db.Integer, default=0)
    report_time = db.Column(db.Integer, default=0)
    saved = db.Column(db.Boolean, default=False)
    top = db.Column(db.Boolean, default=False)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    top_timestamp = db.Column(db.String(60))

    group = db.relationship('Group', back_populates='topics')
    posts = db.relationship('Post', back_populates='topic', cascade='all')
    receivers = db.relationship('Notice', back_populates='noticed', cascade='all')
    author = db.relationship('User', back_populates='topics')
    files = db.relationship('File', back_populates='topic', cascade='all')
    collectors = db.relationship('Collect', back_populates='collected', cascade='all')
    readers = db.relationship('Read', back_populates='readed', cascade='all')

    def __init__(self, **kwargs):
        super(Topic, self).__init__(**kwargs)

    def get_last_post(self):
        if self.posts:
            last_post = Post.query.with_parent(self).filter_by(saved=False).order_by(Post.timestamp.desc()).first()
        else:
            last_post = None
        return last_post

    def get_post_count(self):
        post_count = Post.query.with_parent(self).filter_by(saved=False).count()
        return post_count


@whooshee.register_model('title', 'body')
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(60), nullable=False)
    body = db.Column(db.Text, nullable=False)
    saved = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    report_time = db.Column(db.Integer, default=0)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'))
    replied_id = db.Column(db.Integer, db.ForeignKey('post.id'))

    files = db.relationship('File', back_populates='post', cascade='all')
    author = db.relationship('User', back_populates='posts')
    topic = db.relationship('Topic', back_populates='posts')
    replies = db.relationship('Post', back_populates='replied', cascade='all')
    replied = db.relationship('Post', back_populates='replies', remote_side=[id])


class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(64))
    filename_s = db.Column(db.String(64))
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), index=True)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), index=True)

    post = db.relationship('Post', back_populates='files')
    topic = db.relationship('Topic', back_populates='files')


@db.event.listens_for(File, 'after_delete', named=True)
def delete_files(**kwargs):
    target = kwargs['target']
    for filename in [target.filename, target.filename_s]:
        if filename is not None:  #filename_s may be None
            path = os.path.join(current_app.config['UPLOAD_PATH'], filename)
            if os.path.exists(path):
                os.remove(path)


@whooshee.register_model('username', 'name')
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), unique=True, index=True)
    username = db.Column(db.String(30), unique=True)
    name = db.Column(db.String(30))
    phone = db.Column(db.String(30))
    password_hash = db.Column(db.String(128))
    member_since = db.Column(db.DateTime, default=datetime.utcnow)
    position = db.Column(db.String(30))
    company = db.Column(db.String(30))
    avatar_s = db.Column(db.String(64))
    avatar_m = db.Column(db.String(64))
    avatar_l = db.Column(db.String(64))
    avatar_raw = db.Column(db.String(64))
    receive_collect_notification = db.Column(db.Boolean, default=True)
    receive_post_notification = db.Column(db.Boolean, default=True)
    receive_notice_notification = db.Column(db.Boolean, default=True)

    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    confirmed = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)

    posts = db.relationship('Post', back_populates='author', cascade='all')
    role = db.relationship('Role', back_populates='users')
    admin_groups = db.relationship('Group', back_populates='admin')
    notifications = db.relationship('Notification', back_populates='receiver', cascade='all')
    collections = db.relationship('Collect', back_populates='collector', cascade='all')
    reads = db.relationship('Read', back_populates='reader', cascade='all')
    notices = db.relationship('Notice', back_populates='receiver', cascade='all')
    topics = db.relationship('Topic', back_populates='author', cascade='all')

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        self.generate_avatar()
        self.set_role()

    def generate_avatar(self):
        avatar = Identicon()
        filenames = avatar.generate(text=uuid.uuid4().hex)
        self.avatar_s = filenames[0]
        self.avatar_m = filenames[1]
        self.avatar_l = filenames[2]
        db.session.commit()

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def validate_password(self, password):
        return check_password_hash(self.password_hash, password)

    def set_role(self):
        if self.role is None:
            if self.email == current_app.config['ADMIN_EMAIL']:
                self.role = Role.query.filter_by(name='管理员').first()
            else:
                self.role = Role.query.filter_by(name='普通用户').first()
            db.session.commit()

    @property
    def is_admin(self):
        return self.role.name == '管理员'

    @property
    def is_active(self):
        return self.active

    def can(self, permission_name):
        permission = Permission.query.filter_by(name=permission_name).first()
        return permission is not None and self.role is not None and permission in self.role.permissions

    def collect(self, topic):
        if not self.is_collecting(topic):
            collect = Collect(collector=self, collected=topic)
            db.session.add(collect)
            db.session.commit()

    def uncollect(self, topic):
        collect = Collect.query.with_parent(self).filter_by(collected_id=topic.id).first()
        if collect:
            db.session.delete(collect)
            db.session.commit()

    def is_collecting(self, topic):
        return Collect.query.with_parent(self).filter_by(collected_id=topic.id).first() is not None

    def is_reading(self, topic):
        return Read.query.with_parent(self).filter_by(readed_id=topic.id).first() is not None

    def read(self, topic):
        if not self.is_reading(topic):
            read = Read(reader=self, readed=topic)
            db.session.add(read)
            db.session.commit()

    def is_noticing(self, topic):
        return Notice.query.with_parent(self).filter_by(noticed_id=topic.id).first() is not None

    def notice(self, topic):
        if not self.is_noticing(topic):
            notice = Notice(receiver=self, noticed=topic)
            db.session.add(notice)
            db.session.commit()

    def unnotice(self, topic):
        if self.is_noticing(topic):
            notice = Notice.query.with_parent(self).filter_by(noticed_id=topic.id).first()
            db.session.delete(notice)
            db.session.commit()

    def publish_post_count(self):
        post_count = Post.query.with_parent(self).filter_by(saved=False).count()
        return post_count

    def saved_post_count(self):
        count = Post.query.with_parent(self).filter_by(saved=True).count()
        return count

    def publish_topic_count(self):
        count = Topic.query.with_parent(self).filter_by(saved=False).count()
        return count

    def saved_topic_count(self):
        count = Topic.query.with_parent(self).filter_by(saved=True).count()
        return count

    def block(self):
        self.active = False
        db.session.commit()

    def unblock(self):
        self.active = True
        db.session.commit()


@db.event.listens_for(User, 'after_delete', named=True)
def delete_avatars(**kwargs):
    target = kwargs['target']
    for filename in [target.avatar_s, target.avatar_m, target.avatar_l, target.avatar_raw]:
        if filename is not None:  # avatar_raw may be None
            path = os.path.join(current_app.config['AVATARS_SAVE_PATH'], filename)
            if os.path.exists(path):  # not every filename map a unique file
                os.remove(path)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    receiver = db.relationship('User', back_populates='notifications')
