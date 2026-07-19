from flask_wtf import FlaskForm
from wtforms import DateField, IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional


class RoadmapForm(FlaskForm):
    learning_track = SelectField("Choose Language", choices=[], validators=[DataRequired(), Length(max=120)])
    known_skills = StringField("Completed topics", validators=[Optional(), Length(max=500)])
    current_level = SelectField("Experience level", choices=[("complete_beginner", "Complete Beginner"), ("beginner", "Beginner"), ("intermediate", "Intermediate"), ("advanced", "Advanced")])
    weekly_hours = IntegerField("Available study hours per week", validators=[DataRequired(), NumberRange(min=1, max=80)], default=8)
    target_date = DateField("Optional target date", validators=[Optional()])
    submit = SubmitField("Build roadmap")


class ResumeBuilderForm(FlaskForm):
    title = StringField("Resume title", validators=[DataRequired(), Length(max=160)])
    template = SelectField("Template", choices=[("classic", "Classic ATS"), ("modern", "Modern Compact"), ("technical", "Technical")])
    name = StringField("Full name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    phone = StringField("Phone", validators=[Optional(), Length(max=40)])
    links = StringField("LinkedIn / GitHub / Portfolio", validators=[Optional(), Length(max=300)])
    summary = TextAreaField("Professional summary", validators=[DataRequired(), Length(max=1000)])
    skills = TextAreaField("Skills", validators=[DataRequired(), Length(max=1000)])
    experience = TextAreaField("Experience", validators=[DataRequired(), Length(max=3000)])
    projects = TextAreaField("Projects", validators=[Optional(), Length(max=1600)])
    education = TextAreaField("Education", validators=[DataRequired(), Length(max=1200)])
    submit = SubmitField("Save and score resume")


class InterviewSetupForm(FlaskForm):
    category = SelectField(
        "Question category",
        choices=[("technical", "Technical"), ("hr", "HR"), ("behavioral", "Behavioral"), ("coding", "Coding"), ("mcq", "MCQs")],
    )
    difficulty = SelectField("Difficulty", choices=[("beginner", "Beginner"), ("intermediate", "Intermediate"), ("advanced", "Advanced")])
    submit = SubmitField("Start session")
