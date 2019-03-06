from flask import Blueprint, request, current_app, render_template, flash, redirect, url_for, abort
from flask_login import current_user, logout_user, login_required, fresh_login_required
import os

from blogs.models.blogs import User, Post, Collect, Notice, Topic, Notification
from blogs.forms.user import EditProfileForm, CropAvatarForm, UploadAvatarForm, ChangePasswordForm, \
    NotificationSettingForm, ChangeEmailForm
from blogs.extensions import db, avatars
from blogs.utils import flash_errors, generate_token, validate_token, redirect_back
from blogs.decorators import confirm_required
from blogs.settings import Operations
from blogs.emails import send_user_confirm_email

user_bp = Blueprint('user', __name__)


@user_bp.route('/<username>')
@login_required
@confirm_required
def index(username):
    user = User.query.filter_by(username=username).first()
    if user == current_user and not user.active:
        logout_user()

    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['TOPIC_PER_PAGE']
    pagination = Topic.query.with_parent(user).filter_by(saved=False).order_by(Topic.timestamp.desc()).\
        paginate(page, per_page)
    topics = pagination.items
    return render_template('user/topics.html', user=user, pagination=pagination, topics=topics)


@user_bp.route('/settings/profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.name = form.name.data
        current_user.phone = form.phone.data
        current_user.position = form.position.data
        db.session.commit()
        flash('信息已更新', 'success')
        return redirect(url_for('.index', username=current_user.username))
    form.username.data = current_user.username
    form.name.data = current_user.name
    form.phone.data = current_user.phone
    form.position.data = current_user.position
    return render_template('user/setting/edit_profile.html', form=form)


@user_bp.route('/settings/avatar')
@login_required
@confirm_required
def change_avatar():
    upload_form = UploadAvatarForm()
    crop_form = CropAvatarForm()
    return render_template('user/setting/change_avatar.html', upload_form=upload_form, crop_form=crop_form)


@user_bp.route('/settings/avatar/upload', methods=['POST'])
@login_required
@confirm_required
def upload_avatar():
    form = UploadAvatarForm()
    if form.validate_on_submit():
        image = form.upload.data
        filename = avatars.save_avatar(image)
        current_user.avatar_raw = filename
        db.session.commit()
        flash('图片已上传，请剪切图片。', 'success')
    flash_errors(form)
    return redirect(url_for('.change_avatar'))


@user_bp.route('/settings/avatar/crop', methods=['POST'])
@login_required
@confirm_required
def crop_avatar():
    form = CropAvatarForm()
    if form.validate_on_submit() and current_user.avatar_raw:
        x = form.x.data
        y = form.y.data
        w = form.w.data
        h = form.h.data
        filenames = avatars.crop_avatar(current_user.avatar_raw, x, y, w, h)
        current_user.avatar_s = filenames[0]
        current_user.avatar_m = filenames[1]
        current_user.avatar_l = filenames[2]
        db.session.commit()
        flash('头像已更新', 'success')
    flash_errors(form)
    return redirect(url_for('.change_avatar'))


@user_bp.route('/settings/change-password', methods=['GET', 'POST'])
@fresh_login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit() and current_user.validate_password(form.old_password.data):
        current_user.set_password(form.password.data)
        db.session.commit()
        flash('密码已更新', 'success')
        return redirect(url_for('.index', username=current_user.username))
    form.old_password.data = ''
    return render_template('user/setting/change_password.html', form=form)


@user_bp.route('/settings/notification', methods=['GET', 'POST'])
@login_required
def notification_setting():
    form = NotificationSettingForm()
    if form.validate_on_submit():
        current_user.receive_collect_notification = form.receive_collect_notification.data
        current_user.receive_post_notification = form.receive_post_notification.data
        current_user.receive_notice_notification = form.receive_notice_notification.data
        db.session.commit()
        flash('通知设置已更新', 'success')
        return redirect(url_for('user.index', username=current_user.username))
    form.receive_collect_notification.data = current_user.receive_collect_notification
    form.receive_post_notification.data = current_user.receive_post_notification
    form.receive_notice_notification.data = current_user.receive_notice_notification
    return render_template('user/setting/edit_notification.html', form=form)


@user_bp.route('/my_collections')
@login_required
@confirm_required
def collection():
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['POST_PER_PAGE']
    pagination = Collect.query\
        .with_parent(current_user)\
        .order_by(Collect.timestamp.desc()).paginate(page, per_page)
    collects = pagination.items
    return render_template('user/collections.html', collects=collects, pagination=pagination, user=current_user)


@user_bp.route('/draft_posts')
@login_required
@confirm_required
def draft_post():
    drafts = Post.query.with_parent(current_user).filter_by(saved=True).order_by(Post.timestamp.desc()).all()
    return render_template('user/post_drafts.html', drafts=drafts, user=current_user)


@user_bp.route('/draft_topics')
@login_required
@confirm_required
def draft_topic():
    drafts = Topic.query.with_parent(current_user).filter_by(saved=True).order_by(Topic.timestamp.desc()).all()
    return render_template('user/topic_drafts.html', drafts=drafts, user=current_user)


@user_bp.route('/topics_noticed')
@login_required
@confirm_required
def topics_noticed():
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['TOPIC_PER_PAGE']
    pagination = Notice.query \
        .with_parent(current_user) \
        .order_by(Notice.timestamp.desc()).paginate(page, per_page)
    notices = pagination.items
    return render_template('user/topics_noticed.html', notices=notices, user=current_user, pagination=pagination)


@user_bp.route('/posts/<username>')
@login_required
@confirm_required
def my_posts(username):
    user = User.query.filter_by(username=username).first()
    if user == current_user and not user.active :
        logout_user()
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['TOPIC_PER_PAGE']
    pagination = Post.query.with_parent(user).filter_by(saved=False)\
        .order_by(Post.timestamp.desc()).paginate(page, per_page)
    posts = pagination.items
    return render_template('user/posts.html', posts=posts, pagination=pagination, user=user)


@user_bp.route('/settings/change-email', methods=['GET', 'POST'])
@fresh_login_required
def change_email_request():
    form = ChangeEmailForm()
    if form.validate_on_submit():
        token = generate_token(user=current_user, operation=Operations.CHANGE_EMAIL, new_email=form.email.data.lower())
        send_user_confirm_email(to=form.email.data, user=current_user, token=token)
        flash('确认邮件已发送，请检查你的邮箱。', 'info')
        return redirect(url_for('.index', username=current_user.username))
    return render_template('user/setting/change_email.html', form=form)


@user_bp.route('/change-email/<token>')
@login_required
def change_email(token):
    if validate_token(user=current_user, token=token, operation=Operations.CHANGE_EMAIL):
        flash('邮箱已更新。', 'success')
        return redirect(url_for('.index', username=current_user.username))
    else:
        flash('无效或者过时的令牌', 'warning')
        return redirect(url_for('.change_email_request'))


@user_bp.route('/delete_notification/<int:notification_id>', methods=['POST'])
@login_required
def delete_notification(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.receiver != current_user:
        abort(403)

    db.session.delete(notification)
    db.session.commit()
    flash('已成功删除通知。', 'success')
    return redirect_back()


@user_bp.route('/delete_all_notification', methods=['POST'])
@login_required
def delete_all_notification():
    notifications = Notification.query.with_parent(current_user).all()
    for notification in notifications:
        db.session.delete(notification)
    db.session.commit()
    flash('已成功删除所有通知信息。', 'success')
    return redirect_back()