from flask_wtf import FlaskForm
from wtforms import DecimalField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange


class CareerAssessmentForm(FlaskForm):
    skills = TextAreaField("Technical skills", validators=[DataRequired(), Length(min=2, max=1200)])
    interests = TextAreaField("Career interests", validators=[DataRequired(), Length(min=2, max=1200)])
    cgpa = DecimalField("CGPA", validators=[DataRequired(), NumberRange(min=0, max=10)], places=2)
    certifications = StringField("Certifications", validators=[Length(max=500)])
    submit = SubmitField("Recommend career")
