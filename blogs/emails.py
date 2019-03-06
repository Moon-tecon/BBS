from threading import Thread

from flask import current_app, render_template
from flask_mail import Message

from blogs.extensions import mail


def _send_async_mail(app, message):
    with app.app_context():
        mail.send(message)


def send_mail(to, subject, template, **kwargs):
    message = Message(current_app.config['MAIL_SUBJECT_PREFIX'] + subject, recipients=[to])
    message.body = render_template(template + '.txt', **kwargs)
    message.html = render_template(template + '.html', **kwargs)
    app = current_app._get_current_object()
    thr = Thread(target=_send_async_mail, args=[app, message])
    thr.start()
    return thr


def send_notice_email(user, to=None):
    send_mail(subject='通知邮件', to=to or user.email, template='emails/inform', user=user)


def send_reset_password_email(user, token):
    send_mail(subject='密码重置', to=user.email, template='emails/reset_password', user=user, token=token)


def send_confirm_email(user):
    to = current_app.config['ADMIN_EMAIL']
    send_mail(subject='有新用户申请加入泰科论坛', to=to, template='emails/confirm', user=user)


def send_new_post_email(receiver, topic, user):
    send_mail(subject='您关注的文章有新回复', to=receiver.email, template='emails/new_post', topic=topic, user=user,
              receiver=receiver)


def send_user_confirm_email(user, token, to=None):
    send_mail(subject='邮箱确认', to=to or user.email, template='emails/user_confirm', user=user, token=token)
