from flask_wtf import FlaskForm
from wtforms import SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length


class ChatForm(FlaskForm):
    message = TextAreaField("Ask CareerPath AI", validators=[DataRequired(), Length(min=2, max=2000)])
    submit = SubmitField("Send")
