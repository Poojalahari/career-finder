from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import CareerAssessment, ChatConversation, ChatMessage

from .forms import ChatForm
from .services import career_reply

bp = Blueprint("chatbot", __name__, url_prefix="/chat")


@bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    conversation = latest_or_create_conversation()
    return conversation_view(conversation.id)


@bp.route("/<int:conversation_id>", methods=["GET", "POST"])
@login_required
def conversation_view(conversation_id):
    conversation = owned_conversation(conversation_id)
    form = ChatForm()
    if form.validate_on_submit():
        latest = (
            CareerAssessment.query.filter_by(user_id=current_user.id)
            .order_by(CareerAssessment.created_at.desc())
            .first()
        )
        db.session.add(ChatMessage(conversation_id=conversation.id, role="user", content=form.message.data))
        db.session.add(
            ChatMessage(
                conversation_id=conversation.id,
                role="assistant",
                content=career_reply(form.message.data, latest.recommended_career if latest else None),
            )
        )
        db.session.commit()
        return redirect(url_for("chatbot.conversation_view", conversation_id=conversation.id))
    conversations = ChatConversation.query.filter_by(user_id=current_user.id, archived=False).order_by(ChatConversation.updated_at.desc()).all()
    return render_template("chatbot/index.html", form=form, conversation=conversation, conversations=conversations)


@bp.post("/new")
@login_required
def new_conversation():
    conversation = ChatConversation(user_id=current_user.id, title="Career chat")
    db.session.add(conversation)
    db.session.commit()
    return redirect(url_for("chatbot.conversation_view", conversation_id=conversation.id))


@bp.post("/<int:conversation_id>/archive")
@login_required
def archive_conversation(conversation_id):
    conversation = owned_conversation(conversation_id)
    conversation.archived = True
    db.session.commit()
    flash("Conversation archived.", "success")
    return redirect(url_for("chatbot.index"))


@bp.post("/<int:conversation_id>/delete")
@login_required
def delete_conversation(conversation_id):
    conversation = owned_conversation(conversation_id)
    db.session.delete(conversation)
    db.session.commit()
    flash("Conversation deleted.", "success")
    return redirect(url_for("chatbot.index"))


def latest_or_create_conversation():
    conversation = ChatConversation.query.filter_by(user_id=current_user.id, archived=False).order_by(ChatConversation.updated_at.desc()).first()
    if conversation:
        return conversation
    conversation = ChatConversation(user_id=current_user.id, title="Career chat")
    db.session.add(conversation)
    db.session.commit()
    return conversation


def owned_conversation(conversation_id):
    conversation = db.session.get(ChatConversation, conversation_id)
    if not conversation or conversation.user_id != current_user.id:
        abort(404)
    return conversation
