# coding=utf-8
import os
from datetime import datetime
from flask import current_app

from blogs.extensions import db


class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(64))
    filename_s = db.Column(db.String(64))
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'))

    item = db.relationship('Item')


@db.event.listens_for(Photo, 'after_delete', named=True)
def delete_photos(**kwargs):
    target = kwargs['target']
    for filename in [target.filename, target.filename_s]:
        path = os.path.join(current_app.config['TECON_PATH'], filename)
        if os.path.exists(path):                # not every filename map a unique file
            os.remove(path)


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60))
    body = db.Column(db.Text)
    saved = db.Column(db.Boolean, default=False)
    series_id = db.Column(db.Integer, db.ForeignKey('series.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    photo = db.relationship('Photo', uselist=False, cascade='all')
    series = db.relationship('Series', back_populates='items')


class Series(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(10))

    items = db.relationship('Item', back_populates='series', cascade='all')

    @staticmethod
    def init_series():
        series_list = ['关于我们', '产品布局', '新闻中心']
        for name in series_list:
            series = Series.query.filter_by(name=name).first()
            if series is None:
                series = Series(name=name)
                db.session.add(series)
        db.session.commit()