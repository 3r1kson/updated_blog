from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, URL, Email
from flask_ckeditor import CKEditorField


# WTForm for creating a blog post
class NewPost(FlaskForm):
    title = StringField("Title", [DataRequired()])
    subtitle = StringField("Subtitle", [DataRequired()])
    img_url = StringField("Image url", [DataRequired()])
    body = CKEditorField('Body', [DataRequired()])
    submit = SubmitField(label="Submit Post")

# TODO: Create a RegisterForm to register new users
class RegisterForm(FlaskForm):
    name = StringField("Nome", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = StringField("Password", validators=[DataRequired()])
    submit = SubmitField("Save user")

# TODO: Create a LoginForm to login existing users
class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = StringField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

# TODO: Create a CommentForm so users can leave comments below posts
class CommentForm(FlaskForm):
    body = CKEditorField('Comment', [DataRequired()])
    submit = SubmitField("Submit comment")