from flask import Blueprint, flash, redirect, url_for, request, current_app, render_template
from flask_login import login_required

from blogs.models.blogs import User, Post, Topic, Group, Status, Role
from blogs.forms.admin import NewUserForm, NewGroupForm, MigrateForm, EditGroupForm, EditProfileAdminForm
from blogs.extensions import db
from blogs.utils import redirect_back
from blogs.emails import send_notice_email
from blogs.decorators import admin_required, permission_required

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/')
@login_required
@permission_required('MODERATE')
def index():
    group_count = Group.query.count()
    user_count = User.query.filter_by(confirmed=True).count()
    blocked_user_count = User.query.filter_by(active=False).count()
    unconfirm_user_count = User.query.filter_by(confirmed=False).count()
    topic_count = Topic.query.filter_by(saved=False).count()
    post_count = Post.query.filter_by(saved=False).count()
    reported_post_count = Post.query.filter(Post.report_time>0).count()
    reported_topic_count = Topic.query.filter(Topic.report_time>0).count()
    return render_template('admin/index.html', group_count=group_count, user_count=user_count,
                           blocked_user_count=blocked_user_count, topic_count=topic_count, post_count=post_count,
                           reported_post_count=reported_post_count, reported_topic_count=reported_topic_count,
                           unconfirm_user_count=unconfirm_user_count)


@admin_bp.route('/manage_user')
@login_required
@permission_required('MODERATE')
def manage_user():
    filter_rule = request.args.get('filter', 'confirmed')
    # 'confirmed', 'blocked', 'admin', 'moderator', 'unconfirm', 'member'
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['USERS_PER_PAGE']
    admin = Role.query.filter_by(name='管理员').first()
    moderator = Role.query.filter_by(name='协管员').first()
    member = Role.query.filter_by(name='员工').first()
    users = User.query
    if filter_rule == 'confirmed':
        users = users.filter_by(confirmed=True)
    elif filter_rule == 'unconfirm':
        users = users.filter_by(confirmed=False)
    elif filter_rule == 'blocked':
        users = users.filter_by(active=False)
    elif filter_rule == 'member':
        users = users.filter_by(role=member)
    elif filter_rule == 'moderator':
        users = users.filter_by(role=moderator)
    elif filter_rule == 'admin':
        users = users.filter_by(role=admin)

    pagination = users.order_by(User.member_since.desc()).paginate(
        page, per_page)
    users = pagination.items
    return render_template('admin/manage_users.html', users=users, pagination=pagination)


@admin_bp.route('/new_user', methods=['GET', 'POST'])
@login_required
@permission_required('MODERATE')
def new_user():
    form = NewUserForm()
    if form.validate_on_submit():
        username = form.username.data
        name = form.name.data
        email = form.email.data
        role_id = form.role.data
        company = form.company.data
        position = form.position.data
        phone = form.phone.data
        password = current_app.config['DEFAULT_PASSWORD']
        user = User(email=email, username=username, role_id=role_id, company=company, name=name, position=position,
                    phone=phone,  confirmed = True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        send_notice_email(user)
        flash('邮件已发送', 'info')
        return redirect(url_for('.manage_user'))
    return render_template('admin/new_user.html', form=form)


@admin_bp.route('/delete_user/<username>', methods=['POST'])
@login_required
@permission_required('MODERATE')
def delete_user(username):
    user = User.query.filter_by(username=username).first()
    if user.is_admin:
        flash('不可删除管理员', 'danger')
        return redirect_back()
    else:
        db.session.delete(user)
        db.session.commit()
        flash('已删除此用户', 'success')
        return redirect_back()


@admin_bp.route('/confirm/<username>', methods=['POST'])
@login_required
@permission_required('MODERATE')
def confirm(username):
    user = User.query.filter_by(username=username).first()
    user.confirmed = True
    db.session.commit()
    send_notice_email(user)
    return redirect_back()


@admin_bp.route('/reported_posts')
@login_required
@permission_required('MODERATE')
def reported_posts():
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['POST_PER_PAGE']
    pagination = Post.query.filter(Post.report_time > 0). \
        order_by(Post.report_time.desc()).paginate(page, per_page)
    posts = pagination.items
    return render_template('admin/reported_posts.html', posts=posts, pagination=pagination)


@admin_bp.route('/reported_post/<int:post_id>/reset', methods=['POST'])
@login_required
@permission_required('MODERATE')
def reset_post(post_id):
    post = Post.query.get_or_404(post_id)
    post.report_time = 0
    post.saved = False
    db.session.commit()
    flash('帖子的举报次数已清零。', 'success')
    return redirect_back()


@admin_bp.route('/reported_topics')
@login_required
@permission_required('MODERATE')
def reported_topics():
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['POST_PER_PAGE']
    pagination = Topic.query.filter(Topic.report_time > 0). \
        order_by(Topic.report_time.desc()).paginate(page, per_page)
    topics = pagination.items
    return render_template('admin/reported_topics.html', topics=topics, pagination=pagination)


@admin_bp.route('/reported_topic/<int:topic_id>/reset', methods=['POST'])
@login_required
@permission_required('MODERATE')
def reset_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    topic.report_time = 0
    topic.saved = False
    db.session.commit()
    flash('主题的举报次数已清零。', 'success')
    return redirect_back()


@admin_bp.route('/new_group', methods=['GET', 'POST'])
@login_required
@permission_required('MODERATE')
def new_group():
    form = NewGroupForm()
    if form.validate_on_submit():
        name = form.name.data
        admin = User.query.filter_by(username=form.admin.data).first()
        status = Status.query.get(form.status.data)
        intro = form.intro.data
        group = Group(name=name, admin=admin, status=status, intro=intro)
        db.session.add(group)
        db.session.commit()
        flash('新组已建成', 'success')
        return redirect(url_for('main.show_group', group_id=group.id))
    return render_template('admin/new_group.html', form=form)


@admin_bp.route('/delete_group/<int:group_id>', methods=['POST'])
@login_required
@permission_required('MODERATE')
def delete_group(group_id):
    if group_id == 3:
        flash('不可删除', 'danger')
    else:
        group = Group.query.get_or_404(group_id)
        db.session.delete(group)
        db.session.commit()
        flash('小组已删除', 'success')
    return redirect_back()


@admin_bp.route('/manage_group', methods=['POST', 'GET'])
@login_required
@permission_required('MODERATE')
def manage_group():
    groups = Group.query.all()
    form = MigrateForm()
    return render_template('admin/manage_groups.html', groups=groups, form=form)


@admin_bp.route('/migrate_group/<int:group_id>', methods=['POST'])
@login_required
@permission_required('MODERATE')
def migrate_group(group_id):
    group = Group.query.get_or_404(group_id)
    form = MigrateForm()
    if form.validate_on_submit():
        for topic in group.topics:
            topic.group_id = form.group.data
        db.session.commit()
        flash('组内主题已迁移成功。', 'success')
        return redirect_back()


@admin_bp.route('/group/<int:group_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('MODERATE')
def edit_group(group_id):
    group = Group.query.get_or_404(group_id)
    form = EditGroupForm(group=group)
    if form.validate_on_submit():
        group.name = form.name.data
        group.intro = form.intro.data
        group.status_id = form.status.data
        admin = User.query.filter_by(username=form.admin.data).first()
        group.admin = admin
        db.session.commit()
        flash('组信息已更新成功', 'success')
        return redirect(url_for('.manage_group'))
    form.name.data = group.name
    form.intro.data = group.intro
    form.admin.data = group.admin.username
    form.status.data = group.status_id
    return render_template('admin/edit_group.html', form=form, group=group)


@admin_bp.route('/profile/<username>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(username):
    user = User.query.filter_by(username=username).first()
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.username = form.username.data
        user.name = form.name.data
        user.phone = form.phone.data
        user.position = form.position.data
        user.email = form.email.data
        user.role = Role.query.get(form.role.data)
        user.confirmed = form.confirmed.data
        user.active = form.active.data
        db.session.commit()
        flash('用户信息已更新', 'success')
        return redirect(url_for('admin.index'))
    form.username.data = user.username
    form.name.data = user.name
    form.phone.data = user.phone
    form.position.data = user.position
    form.email.data = user.email
    form.role.data = user.role_id
    form.confirmed.data = user.confirmed
    form.active.data = user.active
    return render_template('admin/edit_profile.html', form=form, user=user)


@admin_bp.route('/migrate/topic/<int:topic_id>', methods=['POST'])
@login_required
@permission_required('MODERATE')
def migrate_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    form = MigrateForm()
    if form.validate_on_submit():
        topic.group_id = form.group.data
        db.session.commit()
        return redirect(url_for('main.show_group', group_id=topic.group_id))
