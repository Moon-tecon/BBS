from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField, HiddenField, PasswordField, BooleanField
from wtforms.validators import Length, DataRequired, Regexp, EqualTo, ValidationError, Optional, Email
from flask_wtf.file import FileField, FileAllowed, FileRequired
from flask_login import current_user

from blogs.models.blogs import User


class EditProfileForm(FlaskForm):
    username = StringField('用户名*', validators=[DataRequired(), Length(1, 30),
                                               Regexp('^[a-zA-Z0-9]*$', message='用户名只能由a-z,A-Z和0-9组成。')])
    name = StringField('真实姓名', validators=[Length(0, 20), Optional()])
    phone = StringField('手机号码', validators=[Optional(), Length(1, 11),
                                            Regexp("^1(?:3\d|4[4-9]|5[0-35-9]|6[67]|7[013-8]|8\d|9\d)\d{8}$")])
    position = StringField('职位', validators=[Optional(), Length(0, 30)])
    submit = SubmitField('更新')

    def validate_username(self, field):
        if field.data != current_user.username and User.query.filter_by(username=field.data).first():
            raise ValidationError('用户名已存在。')



class UploadAvatarForm(FlaskForm):
    upload = FileField('上传图片', validators=[FileRequired(), FileAllowed(['jpg', 'png'],
                                                                       '仅允许 .jpg 或者 .png后缀的图片。')])
    submit = SubmitField('上传')


class CropAvatarForm(FlaskForm):
    x = HiddenField()
    y = HiddenField()
    w = HiddenField()
    h = HiddenField()
    submit = SubmitField('剪切并保存')


class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('旧密码', validators=[DataRequired(), Length(8, 128)])
    password = PasswordField('新密码', validators=[DataRequired(), Length(8, 128), EqualTo('password2')])
    password2 = PasswordField('请再输一次新密码', validators=[DataRequired(), Length(8, 128)])
    submit = SubmitField('保存')


class NotificationSettingForm(FlaskForm):
    receive_post_notification = BooleanField('新回帖通知')
    receive_collect_notification = BooleanField('新收藏者通知')
    receive_notice_notification = BooleanField('新订阅者通知')
    submit = SubmitField('保存')


class ChangeEmailForm(FlaskForm):
    email = StringField('新邮箱', validators=[DataRequired(), Length(1, 254), Email()])
    submit = SubmitField('提交')

    def validate_email(self, field):
        if field.data != self.user.email and User.query.filter_by(email=field.data).first():
            raise ValidationError('此邮箱已注册过本论坛。')
