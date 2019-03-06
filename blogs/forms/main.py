from flask_wtf import FlaskForm
from wtforms import SubmitField, SelectField, StringField, BooleanField
from wtforms.validators import Optional, Length, DataRequired, ValidationError
from flask_ckeditor import CKEditorField


class PostForm(FlaskForm):
    title = StringField('标题', validators=[DataRequired(), Length(1, 60)])
    body = CKEditorField('', validators=[DataRequired(message='内容不能为空！'), Length(1, 100000)])
    notice = BooleanField('有人回复时，给我发送一封Email')
    save = SubmitField('保存草稿')
    publish = SubmitField('发布')
    save1 = SubmitField('附件')