from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms import ValidationError
from wtforms.validators import DataRequired, Length, Email, EqualTo, Regexp

from blogs.models.blogs import User


class LoginForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(1, 30)])
    password = PasswordField('密码', validators=[DataRequired()])
    remember_me = BooleanField('记住账号')
    submit = SubmitField('登录')


class ForgetPasswordForm(FlaskForm):
    email = StringField('邮箱', validators=[DataRequired(), Length(1, 254), Email()])
    submit = SubmitField('提交')


class ResetPasswordForm(FlaskForm):
    email = StringField('邮箱', validators=[Email(), DataRequired(), Length(1, 254)])
    password = PasswordField('密码', validators=[
        DataRequired(), Length(8, 128), EqualTo('password2')], render_kw={'placeholder': '请输入不少于8位数的密码'})
    password2 = PasswordField('请再输一次密码', validators=[DataRequired()])
    submit = SubmitField('保存')


class RegisterForm(FlaskForm):
    username = StringField('用户名*', validators=[DataRequired(), Length(1, 30),
                                               Regexp('^[a-zA-Z0-9]*$',
                                                      message='用户名只能由a-z,A-Z和0-9组成。')])
    name = StringField('真实姓名*', validators=[DataRequired(), Length(1, 30)])
    email = StringField('Email*', validators=[DataRequired(), Length(1, 254), Email()])
    company = StringField('公司名称*', validators=[DataRequired(), Length(1, 30)],
                          render_kw={'placeholder': '请输入公司名称，以便确认账号'})
    password = PasswordField('密码*', validators=[
        DataRequired(), Length(8, 128), EqualTo('password2')], render_kw={'placeholder': '请输入不少于8位数的密码'})
    password2 = PasswordField('确认密码*', validators=[DataRequired()])
    submit = SubmitField('注册')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('邮箱地址已经存在。')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('用户名已存在。')



