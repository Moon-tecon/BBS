from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, SelectField, BooleanField
from wtforms.validators import Length, DataRequired, Email, Regexp, Optional, ValidationError, AnyOf

from blogs.models.blogs import User, Role, Status, Group
from blogs.forms.user import EditProfileForm


class NewUserForm(FlaskForm):
    username = StringField('用户名*', validators=[Length(1, 30), DataRequired(),
                                               Regexp('^[a-zA-Z0-9]*$', message='用户名只能由a-z,A-Z和0-9组成。')])
    name = StringField('姓名', validators=[Length(0, 30), Optional()])
    email = StringField('邮箱*', validators=[Email(), DataRequired(), Length(1, 254)])
    company = StringField('公司名', validators=[Length(0, 30), Optional()])
    position = StringField('职位', validators=[Length(0, 30), Optional()])
    phone = StringField('手机号码',  validators=[Optional(), Length(1, 11),
                                            Regexp("^1(?:3\d|4[4-9]|5[0-35-9]|6[67]|7[013-8]|8\d|9\d)\d{8}$")])
    role = SelectField('角色', validators=[DataRequired('请选择')], render_kw={'class': 'form-control'},
                       choices=[(1, '用户'), (2, '员工')], coerce=int, default=2)
    submit = SubmitField('加入')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('用户名已存在')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('邮箱已存在')


class NewGroupForm(FlaskForm):
    name = StringField('组名*', validators=[DataRequired(), Length(1, 30)])
    admin = StringField('小组管理员用户名', validators=[Optional(), Length(1, 30)])
    status = SelectField('级别*', coerce=int, default=1)
    intro = TextAreaField('简介', validators=[Length(0, 500), Optional()])
    submit = SubmitField('提交')

    def __init__(self, *args, **kwargs):
        super(NewGroupForm, self).__init__(*args, **kwargs)
        self.status.choices = [(status.id, status.name)
                               for status in Status.query.order_by(Status.name).all()]

    def validate_admin(self, field):
        if not User.query.filter_by(username=field.data).first():
            raise ValidationError('此人未加入本论坛。')

    def validate_name(self, field):
        if Group.query.filter_by(name=field.data).first():
            raise ValidationError('组名已存在。')


class MigrateForm(FlaskForm):
    group = SelectField('组名', coerce=int)
    submit = SubmitField('迁移')

    def __init__(self, *args, **kwargs):
        super(MigrateForm, self).__init__(*args, **kwargs)
        self.group.choices = [(group.id, group.name)
                               for group in Group.query.order_by(Group.name).all()]



class EditGroupForm(NewGroupForm):
    def __init__(self, group, *args, **kwargs):
        super(EditGroupForm, self).__init__(*args, **kwargs)
        self.status.choices = [(status.id, status.name)
                               for status in Status.query.order_by(Status.name).all()]
        self.group = group

    def validate_admin(self, field):
        if not User.query.filter_by(username=field.data).first():
            raise ValidationError('此人未加入本论坛。')

    def validate_name(self, field):
        if field.data != self.group.name and Group.query.filter_by(name=field.data).first():
            raise ValidationError('组名已存在。')


class EditProfileAdminForm(EditProfileForm):
    email = StringField('Email', validators=[DataRequired(), Length(1, 254), Email()])
    role = SelectField('角色', coerce=int)
    active = BooleanField('Active')
    confirmed = BooleanField('确认')
    submit = SubmitField('更新')

    def __init__(self, user, *args, **kwargs):
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)
        self.role.choices = [(role.id, role.name)
                             for role in Role.query.order_by(Role.name).all()]
        self.user = user

    def validate_username(self, field):
        if field.data != self.user.username and User.query.filter_by(username=field.data).first():
            raise ValidationError('用户名已存在。')

    def validate_email(self, field):
        if field.data != self.user.email and User.query.filter_by(email=field.data).first():
            raise ValidationError('此邮箱已注册过本论坛。')