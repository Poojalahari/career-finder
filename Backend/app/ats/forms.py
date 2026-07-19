from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import Length


class ResumeScanForm(FlaskForm):
    resume = FileField("PDF resume", validators=[FileRequired(), FileAllowed(["pdf"], "Only PDF files are accepted.")])
    job_title = StringField("Target job title", validators=[Length(max=160)])
    job_description = TextAreaField("Job description", validators=[Length(max=8000)])
    submit = SubmitField("Analyze resume")
