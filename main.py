from logging import raiseExceptions

import flask_login
from flask import Flask, render_template, redirect, url_for, flash, request, abort
from functools import wraps
from flask_bootstrap import Bootstrap5
from flask_gravatar import Gravatar
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Text
from flask_wtf import FlaskForm
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, URL
from flask_ckeditor import CKEditor, CKEditorField
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from datetime import date

from forms import NewPost, RegisterForm, LoginForm, CommentForm

'''
Make sure the required packages are installed: 
Open the Terminal in PyCharm (bottom left). 

On Windows type:
python -m pip install -r requirements.txt

On MacOS type:
pip3 install -r requirements.txt

This will install the packages from the requirements.txt for this project.
'''

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
Bootstrap5(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

ckeditor = CKEditor(app)

# CREATE DATABASE
class Base(DeclarativeBase):
    pass
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'
db = SQLAlchemy(model_class=Base)
db.init_app(app)

gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

# TODO: Configure Flask-Login
class User(UserMixin, db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(1000))
    # The "author" refers to the author property in the BlogPost class.
    posts = relationship("BlogPost", back_populates="author")
    # Parent relationship: "comment_author" refers to the comment_author property in the Comment class.
    comments = relationship("Comment", back_populates="comment_author")

class Comment(UserMixin, db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    author_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("user.id"), nullable=False)
    post_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("blog_post.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    comment_author = relationship("User", back_populates="comments")
    parent_post = relationship("BlogPost", back_populates="comments")

    def to_dict(self):
        return {
            "id": self.id,
            "author_id": self.author_id,
            "post_id": self.post_id,
            "body": self.body,
        }

# CONFIGURE TABLE
class BlogPost(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("user.id"), nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)
    comments = relationship("Comment", back_populates="parent_post")
    author = relationship("User", back_populates="posts")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "subtitle": self.subtitle,
            "date": self.date,
            "body": self.body,
            "author": self.author,
            "img_url": self.img_url,
        }

with app.app_context():
    db.create_all()


@app.route('/')
def get_all_posts():
    is_admin = False
    if current_user.is_authenticated:
        is_admin = flask_login.current_user.id == 1
    posts_db = BlogPost.query.all()
    posts = [post.to_dict() for post in posts_db]
    return render_template("index.html", all_posts=posts, logged_in=current_user.is_authenticated, is_admin=is_admin)


# TODO: Add a route so that you can click on individual posts.
@app.route('/<post_id>', methods=['GET', 'POST'])
def show_post(post_id):
    # TODO: Retrieve a BlogPost from the database based on the post_id
    is_admin = flask_login.current_user.id == 1
    requested_post = db.get_or_404(BlogPost, int(post_id))
    comments = Comment.query.filter_by(post_id=int(post_id)).all()
    comment_form = CommentForm()
    comment_form.validate_on_submit()
    if comment_form.validate_on_submit():
        body = " ".join(comment_form.body.data.replace("<p>", "").replace("</p>", "").split())
        comment = Comment(
            author_id=current_user.id,
            post_id=post_id,
            body=body
        )

        db.session.add(comment)
        db.session.commit()

        return redirect(url_for("show_post", post_id=post_id))

    return render_template("post.html", post=requested_post, logged_in=current_user.is_authenticated, is_admin=is_admin, form=comment_form, comments=comments)


# TODO: Use Werkzeug to hash the user's password when creating a new user.
@app.route('/register', methods=["GET", "POST"])
def register():

    form = RegisterForm()
    form.validate_on_submit()
    if request.method == "POST" and form.validate_on_submit():
        hash_and_salted_password = generate_password_hash(
            form.password.data,
            method='pbkdf2:sha256',
            salt_length=8
        )
        user = User(
            name=form.name.data,
            email=form.email.data,
            password=hash_and_salted_password
        )
        user_exists = db.session.query(User).filter_by(email=user.email).first()

        if user_exists:
            flash('Email address already exists')
            return render_template("register.html", form=form)

        db.session.add(user)
        db.session.commit()

        login_user(user)

        return redirect(url_for("get_all_posts"))

    return render_template("register.html", form=form, logged_in=current_user.is_authenticated)


# TODO: Retrieve a user from the database based on their email.
@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    form.validate_on_submit()
    if request.method == "POST" and form.validate_on_submit():
        email = request.form.get("email")
        password = request.form.get("password")

        user = db.session.query(User).filter_by(email=email).first()

        if not user or not check_password_hash(user.password, password):
            flash('Please check your login details and try again.', 'danger')
            return redirect(url_for("login"))

        login_user(user)
        return redirect(url_for("get_all_posts"))

    return render_template("login.html", logged_in=current_user.is_authenticated, form=form)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, user_id)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

def admin_only(function):
    @wraps(function)
    def check_admin(*args, **kwargs):
        if not current_user.is_authenticated or current_user.id != 1:
            abort(403)
        return function(*args, **kwargs)
    return check_admin

# TODO: add_new_post() to create a new blog post
@app.route("/new-post", methods=['GET', 'POST'])
@admin_only
def new_post():
    form = NewPost()
    form.validate_on_submit()
    current_date = date.today().strftime("%B %d, %Y")
    if form.validate_on_submit():
        body = form.body.data.replace("<p>", '').replace('</p>', '')

        post_content = BlogPost(
            title = form.title.data,
            subtitle = form.subtitle.data,
            author = current_user,
            author_id = current_user.id,
            img_url = form.img_url.data,
            date = current_date,
            body = body
        )

        db.session.add(post_content)
        db.session.commit()

        return get_all_posts()

    return render_template("make-post.html", form=form)

# TODO: Use a decorator so only an admin user can edit a post
@app.route("/edit-post/<post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    form = NewPost(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        body=post.body
    )
    if form.validate_on_submit():
        post.title = form.title.data
        post.subtitle = form.subtitle.data
        post.img_url = form.img_url.data
        post.author = current_user
        post.body = form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=form, is_edit=True)

# TODO: Use a decorator so only an admin user can delete a post
@app.route("/delete/<post_id>")
def delete(post_id):
    post = db.get_or_404(BlogPost, post_id)
    if post:
        db.session.delete(post)
        db.session.commit()

    return get_all_posts()

# Below is the code from previous lessons. No changes needed.
@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


if __name__ == "__main__":
    app.run(debug=True, port=5003)
    ckeditor.init_app(app)
