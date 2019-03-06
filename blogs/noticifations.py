from flask import url_for

from blogs.extensions import db
from blogs.models.blogs import Notification


def push_group_admin_notification(group):
    message = '您已被设为 <a href="%s">%s</a> 小组的管理员。' % (url_for('main.show_group', group_id=group.id), group.name)
    notification = Notification(message=message, receiver=group.admin)
    db.session.add(notification)
    db.session.commit()


def push_post_notification(post, receiver):
    message = '您发布的这个<a href="%s">%s</a>有新的回帖。' % \
              (url_for('main.show_topic', topic_id=post.topic_id), post.topic.name)
    notification = Notification(message=message, receiver=receiver)
    db.session.add(notification)
    db.session.commit()


def push_collect_notification(topic, user):
    message = '您发表的<a href="%s">%s</a>已被<a href="%s">%s</a>收藏。' % \
              (url_for('main.show_topic', topic_id=topic.id), topic.name, url_for('user.index', username=user.username),
               user.username)
    notification = Notification(message=message, receiver=topic.author)
    db.session.add(notification)
    db.session.commit()


def push_notice_notification(topic, user):
    message = '您发布的<a href="%s">%s</a>已被<a href="%s">%s</a>订阅。' % \
              (url_for('main.show_topic', topic_id=topic.id), topic.name, url_for('user.index', username=user.username),
               user.username)
    notification = Notification(message=message, receiver=topic.author)
    db.session.add(notification)
    db.session.commit()


def push_max_reported_post_notification(post):
    message = '您发布的<a href="%s">%s</a>被举报已达上限，<a href="%s">编辑</a>？' % \
              (url_for('main.show_post', post_id=post.id), post.title,
               url_for('main.edit_post', post_id=post.id))
    notification = Notification(message=message, receiver=post.author)
    db.session.add(notification)
    db.session.commit()


def push_max_reported_topic_notification(topic):
    message = '您发布的<a href="%s">%s</a>被举报已达上限，<a href="%s">编辑</a>？' % \
              (url_for('main.show_topic', topic_id=topic.id), topic.name,
               url_for('main.edit_topic', topic_id=topic.id))
    notification = Notification(message=message, receiver=topic.author)
    db.session.add(notification)
    db.session.commit()