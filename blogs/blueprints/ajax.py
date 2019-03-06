from flask import Blueprint, jsonify, render_template
from flask_login import current_user

from blogs.models.blogs import User, Notification

ajax_bp = Blueprint('ajax', __name__)


@ajax_bp.route('/get_profile/<int:user_id>')
def get_profile(user_id):
    if not current_user.is_authenticated:
        return jsonify(message='请先登录'), 403
    user = User.query.get_or_404(user_id)
    return render_template('main/profile_popup.html', user=user)


@ajax_bp.route('/notifications-count')
def notifications_count():
    if not current_user.is_authenticated:
        return jsonify(message='请先登录'), 403

    count = Notification.query.with_parent(current_user).filter_by(is_read=False).count()
    return jsonify(count=count)
