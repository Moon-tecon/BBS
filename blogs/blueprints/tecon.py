# coding=utf-8
from flask import Blueprint, render_template, request, redirect, current_app, flash, url_for, send_from_directory
from flask_login import login_required
import os
import PIL
from PIL import Image

from blogs.decorators import permission_required
from blogs.models.tecon import Item, Series, Photo
from blogs.forms.tecon import ItemForm, EditItemForm, UploadForm
from blogs.extensions import db
from blogs.utils import rename_image

view_bp = Blueprint('tecon', __name__)


def resize_image(image, filename, base_width):
    filename, ext = os.path.splitext(filename)
    img = Image.open(image)
    if img.size[0] <= base_width:
        return filename + ext
    w_percent = (base_width / float(img.size[0]))
    h_size = int((float(img.size[1]) * float(w_percent)))
    img = img.resize((base_width, h_size), PIL.Image.ANTIALIAS)

    filename += current_app.config['PHOTO_SUFFIX'][base_width] + ext
    img.save(os.path.join(current_app.config['TECON_PATH'], filename), optimize=True, quality=85)
    return filename


@view_bp.route('/')
def index():
    newses = Item.query.filter_by(saved=False, series_id=3).order_by(Item.timestamp.desc()).limit(3)
    return render_template('tecon/index.html', newses=newses)


@view_bp.route('/item/<int:item_id>')
def show_item(item_id):
    item = Item.query.get_or_404(item_id)
    return render_template('tecon/item.html', item=item)


@view_bp.route('/newses')
def show_newses():
    series = Series.query.filter(Series.name=='新闻中心').first()
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['NEWS_PER_PAGE']
    pagination = Item.query.with_parent(series).filter_by(saved=False).order_by(Item.timestamp.desc()).\
        paginate(page, per_page)
    newses = pagination.items
    return render_template('tecon/newses.html', newses=newses, pagination=pagination)


@view_bp.route('/new_item', methods=['GET', 'POST'])
@login_required
@permission_required('PUBLICITY')
def new_item():
    form = ItemForm()
    if form.validate_on_submit():
        name = form.name.data
        body = form.body.data
        series_id = form.series.data
        item = Item(name=name, body=body, series_id=series_id)
        db.session.add(item)
        if form.save.data:
            item.saved = True
            db.session.commit()
            flash('已保存', 'info')
            return redirect(url_for('.manage'))
        if form.publish.data:
            db.session.commit()
            flash('新项目已发布', 'success')
            return redirect(url_for('.upload', item_id=item.id))
    return render_template('tecon/item_form.html', form=form)


@view_bp.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
@login_required
@permission_required('PUBLICITY')
def edit_item(item_id):
    item = Item.query.get_or_404(item_id)
    form = EditItemForm(item=item)
    if form.validate_on_submit():
        item.name = form.name.data
        item.body = form.body.data
        item.series_id = form.series.data
        if form.save.data:
            item.saved = True
            db.session.commit()
            flash('已保存', 'info')
            return redirect(url_for('.manage'))
        if form.publish.data:
            item.saved = False
            db.session.commit()
            flash('新项目已发布', 'success')
            return redirect(url_for('.manage'))
    form.name.data = item.name
    form.body.data = item.body
    form.series.data = item.series_id
    return render_template('tecon/edit_item.html', form=form, item=item)


@view_bp.route('/delete_item/<int:item_id>', methods=['POST'])
@login_required
@permission_required('PUBLICITY')
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('已删除', 'success')
    return redirect(url_for('.manage'))


@view_bp.route('/manage')
@login_required
@permission_required('PUBLICITY')
def manage():
    draft_count = Item.query.filter_by(saved=True).count()
    news_count = Item.query.filter_by(saved=False, series_id=3).count()
    intro_count = Item.query.filter_by(saved=False, series_id=1).count()
    product_count = Item.query.filter_by(saved=False, series_id=2).count()
    return render_template('tecon/manage.html', draft_count=draft_count, news_count=news_count, intro_count=intro_count,
                           product_count=product_count)


@view_bp.route('/manage_list')
@login_required
@permission_required('PUBLICITY')
def manage_list():
    filter_rule = request.args.get('filter', 'news')  #'news', 'intro', 'product'， 'draft'
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['MANAGE_NEWS_PER_PAGE']
    items = None
    series = None
    if filter_rule == 'news':
        series = Series.query.get(3)
        items = Item.query.with_parent(series).filter_by(saved=False)
    elif filter_rule == 'intro':
        series = Series.query.get(1)
        items = Item.query.with_parent(series).filter_by(saved=False)
    elif filter_rule == 'product':
        series = Series.query.get(2)
        items = Item.query.with_parent(series).filter_by(saved=False)
    elif filter_rule == 'draft':
        items = Item.query.filter_by(saved=True)
    pagination = items.order_by(Item.timestamp.desc()).paginate(page, per_page)
    items = pagination.items
    return render_template('tecon/list.html', items=items, pagination=pagination, series=series)


@view_bp.route('/uploads/<path:filename>')
def get_image(filename):
    return send_from_directory(current_app.config['TECON_PATH'], filename)


@view_bp.route('/upload/<int:item_id>', methods=['POST', 'GET'])
@login_required
@permission_required('PUBLICITY')
def upload(item_id):
    item = Item.query.get_or_404(item_id)
    form = UploadForm()
    if form.validate_on_submit():
        if item.photo:
            db.session.delete(item.photo)
            db.session.commit()
        f = form.photo.data
        filename = rename_image(f.filename)
        f.save(os.path.join(current_app.config['TECON_PATH'], filename))
        filename_s = resize_image(f, filename, current_app.config['PHOTO_SIZE']['small'])
        photo = Photo(filename=filename,
                      filename_s=filename_s,
                      item_id=item_id)
        db.session.add(photo)
        db.session.commit()
        flash('图片已上传', 'success')
        return redirect(url_for('.show_item', item_id=item_id))
    return render_template('tecon/upload.html', item=item, form=form)