from flask import Blueprint, redirect, url_for, flash, render_template
from flask_login import current_user, login_required, login_user, logout_user, login_fresh, confirm_login

from blogs.settings import Operations
from blogs.forms.auth import LoginForm, ForgetPasswordForm, ResetPasswordForm, RegisterForm
from blogs.models.blogs import User
from blogs.extensions import db
from blogs.utils import generate_token, validate_token, redirect_back
from blogs.emails import send_reset_password_email, send_confirm_email

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is not None and user.validate_password(form.password.data):
            if login_user(user, form.remember_me.data):
                flash('登录成功.', 'info')
                return redirect_back()
            else:
                flash('你的账号已被封禁。', 'warning')
                return redirect(url_for('main.index'))
        flash('无效的邮箱或者密码.', 'warning')
    return render_template('auth/login.html', form=form)


@auth_bp.route('/forget-password', methods=['GET', 'POST'])
def forget_password():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = ForgetPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user:
            token = generate_token(user=user, operation=Operations.RESET_PASSWORD)
            send_reset_password_email(user=user, token=token)
            flash('重设密码邮件已发送，请查看你的邮箱。', 'info')
            return redirect(url_for('.login'))
        flash('无效的邮箱.', 'warning')
        form.email.data = ""
        return redirect(url_for('.forget_password'))
    return render_template('auth/reset_password.html', form=form)


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user is None:
            return redirect(url_for('main.index'))
        if validate_token(user=user, token=token, operation=Operations.RESET_PASSWORD,
                          new_password=form.password.data):
            flash('密码已更新', 'success')
            form.email.data = ""
            return redirect(url_for('.login'))
        else:
            flash('链接无效或者超时。', 'danger')
            return redirect(url_for('.forget_password'))
    return render_template('auth/reset_password.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('成功登出', 'info')
    return redirect(url_for('main.index'))


@auth_bp.route('/register', methods=['POST', 'GET'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        name = form.name.data
        email = form.email.data.lower()  # 小写处理
        password = form.password.data
        company = form.company.data
        user = User(username=username, email=email, company=company, name=name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        send_confirm_email(user=user)
        flash('确认邮件已发送给系统管理员，请等待管理员确认', 'info')
        return redirect(url_for('.login'))
    return render_template('auth/register.html', form=form)


@auth_bp.route('/re-authenticate', methods=['GET', 'POST'])
@login_required
def re_authenticate():
    if login_fresh():
        return redirect(url_for('main.index'))

    form = LoginForm()
    if form.validate_on_submit() and current_user.validate_password(form.password.data):
        confirm_login()
        return redirect_back()
    return render_template('auth/login.html', form=form)