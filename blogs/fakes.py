import os
import random
import uuid
import time
from faker import Faker
from sqlalchemy.exc import IntegrityError

from blogs.models.blogs import User, Post, Topic, Group, Status
from blogs.extensions import db

fake = Faker('zh-CN')


def fake_admin():
    admin = User(username='admin',
                 confirmed=True,
                 name=fake.name(),
                 position=fake.job(),
                 phone=fake.phone_number(),
                 email='yun.mao@tecon.cn')
    admin.set_password('12345678')
    db.session.add(admin)
    db.session.commit()


def fake_users(count=20):
    for i in range(count):
        user = User(name=fake.name(),
                    username=fake.user_name(),
                    confirmed=True,
                    email=fake.email(),
                    member_since=fake.date_this_decade(),
                    phone=fake.phone_number(),
                    position=fake.job(),
                    company=fake.company())
        user.set_password('12345678')
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()


def fake_groups(count=5):
    for i in range(count):
        group = Group(name=fake.word(),
                      intro=fake.text(100),
                      admin=User.query.get(random.randint(1, User.query.count())),
                      status_id=random.randint(1, Status.query.count()))
        db.session.add(group)
    db.session.commit()


def fake_topics(count=30):
    for i in range(count):
        topic = Topic(name=fake.sentence(),
                      body=fake.text(500),
                      group_id=random.randint(1, Group.query.count()),
                      author_id=random.randint(1, User.query.count()),
                      timestamp=fake.date_time_this_year()
                      )
        db.session.add(topic)
        #topic.time = topic.timestamp.strftime(format("%m%d%H%M%S"))
    db.session.commit()


def fake_posts(count=100):
    for i in range(count):
        post = Post(title=fake.sentence(),
                    body=fake.text(500),
                    author=User.query.get(random.randint(1, User.query.count())),
                    timestamp=fake.date_time_this_year(),
                    topic_id=random.randint(1, Topic.query.count()))
        db.session.add(post)
        #post.time = post.timestamp.strftime(format("%m%d%H%M%S"))
    db.session.commit()


def fake_collect(count=30):
    for i in range(count):
        user = User.query.get(random.randint(1, User.query.count()))
        user.collect(Topic.query.get(random.randint(1, Topic.query.count())))
    db.session.commit()