from flask import render_template, Blueprint, send_from_directory, current_app, request, redirect, url_for, abort, flash
from flask_login import current_user, login_required
import os
import time
from flask_ckeditor import upload_success, upload_fail
import uuid

from blogs.models.blogs import File, Post, Group, User, Notification, Topic, Read
from blogs.extensions import db
from blogs.forms.main import PostForm
from blogs.utils import redirect_back, resize_image, rename_image
from blogs.noticifations import push_post_notification, push_collect_notification, push_notice_notification, \
    push_max_reported_post_notification, push_max_reported_topic_notification
from blogs.decorators import permission_required, confirm_required
from blogs.emails import send_new_post_email
from blogs.forms.admin import MigrateForm

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    all_groups = Group.query.filter_by(status_id=4).all()
    apart_groups = Group.query.filter_by(status_id=3).all()
    limit_groups = Group.query.filter_by(status_id=2).all()
    member_groups = Group.query.filter_by(status_id=1).all()
    return render_template('main/index.html', all_groups=all_groups, limit_groups=limit_groups,
                           groups=apart_groups, member_groups=member_groups)


@main_bp.route('/new_topic/<int:group_id>', methods=['POST', 'GET'])
@login_required
@confirm_required
def new_topic(group_id):
    if group_id == 3:
        abort(403)
    group = Group.query.get_or_404(group_id)
    if group.status_id == 1 and not current_user.can('MEMBER'):
        abort(403)

    if group.status_id == 2 and not current_user.can('MEMBER'):
        abort(403)

    form = PostForm()
    if form.validate_on_submit():
        title = form.title.data
        body = form.body.data
        topic = Topic(name=title, body=body, group_id=group_id, author=current_user._get_current_object())
        db.session.add(topic)
        if form.publish.data:
            current_user.read(topic)  # 标记自己发表的文章为已读
            db.session.commit()
            if form.notice.data:
                current_user.notice(topic)
            flash('主题已发表', 'success')
            return redirect(url_for('main.show_topic', topic_id=topic.id))
        elif form.save.data:
            topic.saved = True
            db.session.commit()
            flash('主题已保存', 'success')
            return redirect(url_for('user.draft_topic'))
        elif form.save1.data:
            topic.saved = True
            db.session.commit()
            flash('请上传附件', 'info')
            return redirect(url_for('.upload_topic', topic_id=topic.id))
    return render_template('main/new_topic.html', form=form, group=group)


@main_bp.route('/show_topic/<int:topic_id>')
def show_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    topic.read_time += 1
    db.session.commit()
    if topic.saved and current_user != topic.author and not current_user.can('MODERATE'):
        abort(404)
    if not current_user.is_authenticated and topic.group.status_id != 4:
        flash('请登录', 'info')
        return redirect(url_for('auth.login'))

    if current_user.is_authenticated and not current_user.confirmed and topic.group.status_id != 4:
        flash('请等待管理员确认您的账户', 'warning')
        return redirect(url_for('main.index'))

    if not current_user.can('MEMBER') and topic.group.status_id == 1:
        abort(403)

    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['POST_PER_PAGE']
    pagination = Post.query.with_parent(topic).filter_by(saved=False).\
        order_by(Post.timestamp.asc()).paginate(page, per_page)
    posts = pagination.items
    if current_user.is_authenticated:
        current_user.read(topic)
    form = MigrateForm()
    return render_template('main/show_topic.html', topic=topic, posts=posts, pagination=pagination, form=form)


@main_bp.route('/new_post/<int:topic_id>', methods=['POST', 'GET'])
@login_required
@confirm_required
def new_post(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    if topic.group.status_id == 1 and not current_user.can('MEMBER'):
        abort(403)
    if topic.group.status_id == 2 and not current_user.can('MEMBER'):
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        title = form.title.data
        body = form.body.data
        post = Post(title=title, body=body, topic=topic, author=current_user._get_current_object())
        db.session.add(post)
        if form.publish.data:
            db.session.commit()
            if topic.receivers:
                for notice in topic.receivers:
                    send_new_post_email(receiver=notice.receiver, topic=topic, user=current_user)
            if form.notice.data:
                current_user.notice(topic)
            if current_user != topic.author and topic.author.receive_post_notification:
                push_post_notification(post=post, receiver=topic.author)
            flash('帖子已发表', 'success')
            return redirect(url_for('main.show_post', post_id=post.id))
        elif form.save.data:
            post.saved = True
            db.session.commit()
            flash('帖子已保存', 'success')
            return redirect(url_for('user.draft_post'))
        elif form.save1.data:
            post.saved = True
            db.session.commit()
            flash('请上传附件', 'info')
            return redirect(url_for('.upload_post', post_id=post.id))
    form.title.data = 'Re:'+topic.name
    return render_template('main/new_post.html', form=form, topic=topic)


@main_bp.route('/uploads/<path:filename>')
def get_file(filename):
    return send_from_directory(current_app.config['UPLOAD_PATH'], filename)


@main_bp.route('/upload', methods=['POST'])
def upload():
    f = request.files.get('upload')  # 获取上传图片文件对象
    extension = f.filename.split('.')[1].lower()
    if extension not in ['jpg', 'gif', 'png', 'jpeg']:  # 验证文件类型示例
        return upload_fail(message='只能上传图片！')  # 返回upload_fail调用
    filename = uuid.uuid4().hex + '.' + extension
    if os.path.exists(os.path.join(current_app.config['UPLOAD_PATH'], filename)):
        filename = rename_image(filename)
    f.save(os.path.join(current_app.config['UPLOAD_PATH'], filename))
    resize_image(request.files['upload'], filename, current_app.config['PHOTO_SIZE']['medium'])
    url = url_for('.get_file', filename=filename)
    return upload_success(url, filename) # 返回upload_success调用


@main_bp.route('/post/<int:post_id>', methods=['POST', 'GET'])
def show_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.saved and current_user != post.author and not current_user.can('MODERATE'):
        abort(404)
    if not current_user.is_authenticated and post.topic.group.status_id != 4:
        flash('请登录', 'info')
        return redirect(url_for('auth.login'))

    if current_user.is_authenticated and not current_user.confirmed and post.topic.group.status_id != 4:
        flash('请等待管理员确认您的账户', 'warning')
        return redirect(url_for('main.index'))
    if not current_user.can('MEMBER') and post.topic.group.status_id == 1:
        abort(403)
    return render_template('main/post.html', post=post)


@main_bp.route('/avatars/<path:filename>')
def get_avatar(filename):
    return send_from_directory(current_app.config['AVATARS_SAVE_PATH'], filename)


@main_bp.route('/post/<int:post_id>/d', methods=['POST'])
@login_required
@confirm_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if current_user != post.author and current_user != post.topic.group.admin and not current_user.can('MODERATE'):
        abort(403)

    db.session.delete(post)
    db.session.commit()
    flash('成功删除帖子', 'success')
    return redirect_back()


@main_bp.route('/topic/<int:topic_id>/delete', methods=['POST'])
@login_required
@confirm_required
def delete_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    if current_user != topic.group.admin and not current_user.can('MODERATE') and current_user != topic.author:
        abort(403)
    db.session.delete(topic)
    db.session.commit()
    flash('删除主题成功', 'success')
    return redirect_back()


@main_bp.route('/notifications')
@login_required
def show_notifications():
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['NOTIFICATION_PER_PAGE']
    notifications = Notification.query.with_parent(current_user)
    filter_rule = request.args.get('filter')
    if filter_rule == 'unread':
        notifications = notifications.filter_by(is_read=False)

    pagination = notifications.order_by(Notification.timestamp.desc()).paginate(page, per_page)
    notifications = pagination.items
    return render_template('main/notifications.html', pagination=pagination, notifications=notifications)


@main_bp.route('/notification/read/<int:notification_id>', methods=['POST'])
@login_required
def read_notification(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if current_user != notification.receiver:
        abort(403)

    notification.is_read = True
    db.session.commit()
    flash('通知已读。', 'success')
    return redirect(url_for('.show_notifications'))


@main_bp.route('/notifications/read/all', methods=['POST'])
@login_required
def read_all_notification():
    for notification in current_user.notifications:
        notification.is_read = True
    db.session.commit()
    flash('所有通知已读', 'success')
    return redirect(url_for('.show_notifications'))


@main_bp.route('/reply/post/<int:replied_id>', methods=['POST', 'GET'])
@login_required
@confirm_required
def reply_post(replied_id):
    replied = Post.query.get_or_404(replied_id)
    if replied.topic.group.status_id == 1 and not current_user.can('MEMBER'):
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        title = form.title.data
        body = form.body.data
        author = current_user._get_current_object()
        post = Post(body=body,
                    title=title,
                    author=author,
                    topic_id=replied.topic_id,
                    replied_id=replied_id)
        db.session.add(post)
        if form.publish.data:
            db.session.commit()
            if post.topic.receivers:
                for notice in post.topic.receivers:
                    send_new_post_email(receiver=notice.receiver, topic=post.topic, user=current_user)
            if form.notice.data:
                current_user.notice(post.topic)
            if current_user != post.topic.author and post.topic.author.receive_post_notification:
                push_post_notification(post=post, receiver=post.topic.author)
            flash('帖子已发表', 'success')
            return redirect(url_for('main.show_post', post_id=post.id))
        elif form.save.data:
            post.saved = True
            db.session.commit()
            flash('帖子已保存', 'success')
            return redirect(url_for('user.draft_post'))
        elif form.save1.data:
            post.saved = True
            db.session.commit()
            flash('请上传附件', 'info')
            return redirect(url_for('.upload_post', post_id=post.id))
    form.title.data = 'Re：'+replied.title
    return render_template('main/reply_post.html', form=form, replied=replied)


@main_bp.route('/collect/<int:topic_id>', methods=['POST'])
@login_required
@confirm_required
def collect(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    if current_user.is_collecting(topic):
        flash('已收藏过此帖子', 'info')
        return redirect(url_for('main.show_topic', topic_id=topic_id))

    current_user.collect(topic)
    flash('收藏成功', 'success')
    if current_user != topic.author and topic.author.receive_collect_notification:
        push_collect_notification(topic=topic, user=current_user)
    return redirect(url_for('main.show_topic', topic_id=topic.id))


@main_bp.route('/uncollect/<int:topic_id>', methods=['POST'])
@login_required
def uncollect(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    if not current_user.is_collecting(topic):
        flash('还没有收藏此帖子', 'info')
        return redirect(url_for('main.show_topic', topic_id=topic_id))

    current_user.uncollect(topic)
    flash('已取消收藏此帖子。', 'success')
    return redirect(url_for('main.show_topic', topic_id=topic_id))


@main_bp.route('/group/<int:group_id>')
def show_group(group_id):
    group = Group.query.get_or_404(group_id)

    if not current_user.is_authenticated and group.status_id != 4:
        flash('请登录', 'info')
        return redirect(url_for('auth.login'))

    if current_user.is_authenticated and not current_user.confirmed and group.status_id != 4:
        flash('请等待管理员确认您的账户', 'warning')
        return redirect(url_for('main.index'))

    if not current_user.can('MEMBER') and group.status_id == 1:
        abort(403)

    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['TOPIC_PER_PAGE']
    pagination = Topic.query.with_parent(group).filter_by(saved=False, top=False).\
        order_by(Topic.timestamp.desc()).paginate(page, per_page)
    topics = pagination.items
    return render_template('main/group.html', topics=topics, pagination=pagination, group=group)


@main_bp.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
@confirm_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)

    if current_user != post.author and current_user != post.topic.group.admin and not current_user.can('MODERATE'):
        abort(403)

    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.body = form.body.data
        if form.publish.data:
            post.saved = False
            db.session.commit()
            if post.topic.receivers:
                for notice in post.topic.receivers:
                    send_new_post_email(receiver=notice.receiver, topic=post.topic, user=current_user)
            if form.notice.data and not current_user.is_noticing(post.topic):
                current_user.notice(post.topic)
            if post.topic.author!= current_user and post.topic.author.receive_post_notification:
                push_post_notification(post=post, receiver=post.topic.author)
            flash('帖子已发表', 'success')
            return redirect(url_for('main.show_post', post_id=post.id))
        elif form.save.data:
            post.saved = True
            db.session.commit()
            flash('帖子已保存', 'success')
            return redirect(url_for('user.draft_post'))
        elif form.save1.data:
            post.saved = True
            db.session.commit()
            flash('请上传附件', 'info')
            return redirect(url_for('.upload_post', post_id=post.id))
    form.title.data = post.title
    form.body.data = post.body
    return render_template('main/edit_post.html', form=form, post=post)


@main_bp.route('/topic/<int:topic_id>/edit', methods=['GET', 'POST'])
@login_required
@confirm_required
def edit_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    if current_user != topic.author and current_user != topic.group.admin and not current_user.can('MODERATE'):
        abort(403)  #除了主题的author、主题所在组的管理员或者协管员，都不能编辑主题
    form = PostForm()
    if form.validate_on_submit():
        topic.name = form.title.data
        topic.body = form.body.data
        if form.publish.data:
            topic.saved = False
            db.session.commit()
            if form.notice.data and not current_user.is_noticing(topic):
                current_user.notice(topic)
            flash('主题已发表', 'success')
            return redirect(url_for('main.show_topic', topic_id=topic.id))
        elif form.save.data:
            if topic.get_last_post():
                flash('已有回帖，不允许保存。', 'warning')
                return redirect_back()
            else:
                topic.saved = True
                topic.top = False
                db.session.commit()
                flash('主题已保存', 'success')
                return redirect(url_for('user.draft_topic'))
        elif form.save1.data:
            topic.saved = True
            topic.top = False
            db.session.commit()
            flash('请上传附件', 'info')
            return redirect(url_for('.upload_topic', topic_id=topic.id))
    form.title.data = topic.name
    form.body.data = topic.body
    return render_template('main/edit_topic.html', form=form, topic=topic)


@main_bp.route('/file/<int:file_id>/delete', methods=['POST'])
@login_required
@confirm_required
def delete_file(file_id):
    file = File.query.get_or_404(file_id)

    if file.post:
        if current_user != file.post.author and not current_user.can('MODERATE') \
                and current_user != file.post.topic.group.admin:
            abort(403)

    if file.topic:
        if current_user != file.topic.author and not current_user.can('MODERATE') \
                and current_user != file.topic.group.admin:
            abort(403)
    db.session.delete(file)
    db.session.commit()
    flash('已删除附件', 'success')
    return redirect_back()


@main_bp.route('/topic/<int:topic_id>/subscribe', methods=['POST'])
@login_required
def notice(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    if current_user.is_noticing(topic):
        flash('此主题已订阅过', 'info')
        return redirect_back()

    current_user.notice(topic)
    flash('订阅成功', 'success')
    if current_user != topic.author and topic.author.receive_notice_notification:
        push_notice_notification(topic=topic, user=current_user)
    return redirect_back()


@main_bp.route('/topic/<int:topic_id>/unsubscribe', methods=['POST'])
@login_required
def unnotice(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    if not current_user.is_noticing(topic):
        flash('还未订阅此主题', 'info')

    current_user.unnotice(topic)
    flash('已取消订阅此主题', 'success')
    return redirect_back()


@main_bp.route('/post/<int:post_id>/report', methods=['POST'])
@login_required
@permission_required('MEMBER')  #员工才能举报帖子
def report_post(post_id):
    post = Post.query.get_or_404(post_id)
    post.report_time += 1
    db.session.commit()
    if post.report_time>int(current_app.config['MAX_REPORT_TIME']):
        post.saved = True
        db.session.commit()
        push_max_reported_post_notification(post=post)
        flash('帖子的举报次数已达上限, 帖子隐藏', 'info')
    else:
        flash('帖子已被举报', 'success')
    return redirect_back()


@main_bp.route('/topic/<int:topic_id>/report', methods=['POST'])
@login_required
@permission_required('MEMBER')
def report_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    topic.report_time +=1
    db.session.commit()
    if topic.report_time>int(current_app.config['MAX_REPORT_TIME']):
        topic.saved = True
        db.session.commit()
        push_max_reported_topic_notification(topic=topic)
        flash('主题的举报次数已达上限，主题隐藏', 'info')
    else:
        flash('主题已被举报', 'success')
    return redirect_back()


@main_bp.route('/search')
def search():
    q = request.args.get('q', '')
    if q == '':
        flash('请输入要搜索内容的关键字', 'warning')
        return redirect_back()
    if len(q)<2:
        flash('输入字符数不能少于2', 'warning')
        return redirect_back()

    category = request.args.get('category', 'topic')
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['SEARCH_RESULT_PER_PAGE']
    if category == 'user':
        pagination = User.query.whooshee_search(q).paginate(page, per_page)
    elif category == 'post':
        pagination = Post.query.whooshee_search(q).paginate(page, per_page)
    else:
        pagination = Topic.query.whooshee_search(q).paginate(page, per_page)
    results = pagination.items
    return render_template('main/search.html', q=q, results=results, pagination=pagination, category=category)


@main_bp.route('/top_topic/<int:topic_id>', methods=['POST'])
@login_required
@confirm_required
def top_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    if not current_user.can('MODERATE') and current_user != topic.group.admin:
        abort(403)   #只能主题所在组管理员和协管员才能置顶帖子
    topic.top = True
    topic.top_timestamp = time.time()
    db.session.commit()
    flash('主题已置顶。', 'success')
    return redirect_back()


@main_bp.route('/cancel_top_topic/<int:topic_id>', methods=['POST'])
@login_required
@confirm_required
def cancel_top_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    if not current_user.can('MODERATE') and current_user != topic.group.admin:
        abort(403)   #只能主题所在组管理员和协管员才能取消置顶
    topic.top = False
    db.session.commit()
    flash('主题已取消置顶。', 'success')
    return redirect_back()


@main_bp.route('/upload/topic/<int:topic_id>', methods=['GET', 'POST'])
@login_required
@confirm_required
def upload_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    if current_user != topic.author and current_user != topic.group.admin and not current_user.can('MODERATE'):
        abort(403)
    if request.method == 'POST' and 'file' in request.files:
        f = request.files.get('file')
        filename = f.filename
        if os.path.exists(os.path.join(current_app.config['UPLOAD_PATH'], filename)):
            filename = rename_image(filename)
        f.save(os.path.join(current_app.config['UPLOAD_PATH'], filename))
        filename_s = None
        if filename.rsplit('.', 1)[1] in ['jpg', 'png', 'jpeg', 'gif', 'PNG', 'bmp']:
            filename_s = resize_image(request.files['file'], filename, current_app.config['PHOTO_SIZE']['small'])
        file = File(filename=filename, filename_s=filename_s, topic_id=topic_id)
        db.session.add(file)
        db.session.commit()
    return render_template('main/upload_topic.html', topic=topic)


@main_bp.route('/upload/post/<int:post_id>', methods=['GET', 'POST'])
@login_required
@confirm_required
def upload_post(post_id):
    post = Post.query.get_or_404(post_id)
    if current_user != post.author and current_user != post.topic.group.admin and not current_user.can('MODERATE'):
        abort(403)
    if request.method == 'POST' and 'file' in request.files:
        f = request.files.get('file')
        filename = f.filename
        if os.path.exists(os.path.join(current_app.config['UPLOAD_PATH'], filename)):
            filename = rename_image(filename)
        f.save(os.path.join(current_app.config['UPLOAD_PATH'], filename))
        filename_s = None
        if filename.rsplit('.', 1)[1] in ['jpg', 'png', 'jpeg', 'gif', 'PNG', 'bmp']:
            filename_s = resize_image(request.files['file'], filename, current_app.config['PHOTO_SIZE']['small'])
        file = File(filename=filename, filename_s=filename_s, post_id=post_id)
        db.session.add(file)
        db.session.commit()
    return render_template('main/upload_post.html', post=post)


@main_bp.route('/publish/topic/<int:topic_id>', methods=['POST'])
@login_required
@confirm_required
def publish_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    if current_user != topic.author and current_user != topic.group.admin and not current_user.can('MODERATE'):
        abort(403)
    topic.saved = False
    db.session.commit()
    flash('主题已发表', 'success')
    return redirect(url_for('.show_topic', topic_id=topic_id))


@main_bp.route('/publish/post/<int:post_id>', methods=['POST'])
@login_required
@confirm_required
def publish_post(post_id):
    post = Post.query.get_or_404(post_id)
    if current_user != post.author and current_user != post.topic.group.admin and not current_user.can('MODERATE'):
        abort(403)
    post.saved = False
    db.session.commit()
    flash('帖子已发表', 'success')
    return redirect(url_for('.show_post', post_id=post_id))