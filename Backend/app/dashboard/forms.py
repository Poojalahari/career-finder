from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, ValidationError

from app.services.security import password_is_strong


class ProfileForm(FlaskForm):
    full_name = StringField("Full name", validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    submit = SubmitField("Update profile")


class PasswordChangeForm(FlaskForm):
    current_password = PasswordField("Current password", validators=[DataRequired(), Length(max=128)])
    new_password = PasswordField("New password", validators=[DataRequired(), Length(min=10, max=128)])
    confirm_password = PasswordField("Confirm new password", validators=[DataRequired(), EqualTo("new_password")])
    submit = SubmitField("Change password")

    def validate_new_password(self, field):
        if not password_is_strong(field.data):
            raise ValidationError("Use 10+ characters with uppercase, lowercase, number, and symbol.")


class DeleteAccountForm(FlaskForm):
    confirmation = StringField("Type DELETE to confirm", validators=[DataRequired(), Length(max=20)])
    password = PasswordField("Current password", validators=[Optional(), Length(max=128)])
    submit = SubmitField("Delete account")
