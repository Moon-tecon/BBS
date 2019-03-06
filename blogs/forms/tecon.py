# coding=utf-8
from flask_wtf import FlaskForm
from wtforms import SubmitField, SelectField, StringField
from wtforms.validators import Length, DataRequired, ValidationError
from flask_ckeditor import CKEditorField
from flask_wtf.file import FileField, FileRequired, FileAllowed

from blogs.models.tecon import Item, Series


class ItemForm(FlaskForm):
    name = StringField('标题', validators=[DataRequired(), Length(1,60)])
    body = CKEditorField('', validators=[DataRequired(), Length(1, 2000)])
    series = SelectField('类别',  coerce=int)
    save = SubmitField('保存草稿')
    publish = SubmitField('发布')

    def __init__(self, *args, **kwargs):
        super(ItemForm, self).__init__(*args, **kwargs)
        self.series.choices = [(series.id, series.name)
                             for series in Series.query.order_by(Series.name).all()]

    def validate_name(self, field):
        if Item.query.filter_by(name=field.data).first():
            raise ValidationError('标题已存在。')


class EditItemForm(ItemForm):
    def __init__(self, item, *args, **kwargs):
        super(EditItemForm, self).__init__(*args, **kwargs)
        self.series.choices = [(series.id, series.name)
                               for series in Series.query.order_by(Series.name).all()]
        self.item = item

    def validate_name(self, field):
        if field.data != self.item.name and Item.query.filter_by(name=field.data).first():
            raise ValidationError('标题已存在。')


class UploadForm(FlaskForm):
    photo = FileField('', validators=[FileRequired(), FileAllowed(['jpg', 'jpeg', 'png', 'gif'])])
    submit = SubmitField('上传')