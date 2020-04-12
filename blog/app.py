from flask import Flask, render_template, request, redirect, url_for, abort
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager

from datetime import datetime

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Email, EqualTo, Length, InputRequired, DataRequired, ValidationError

from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'
app.config["SECRET_KEY"] = 'dev'
db = SQLAlchemy(app)
manager = Manager(app)
migrate = Migrate(app, db)
manager.add_command('db', MigrateCommand)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


#--------------------------------------------------------------------------------------
#Models

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(25), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(30), nullable=False)

    def __repr__(self):
        return self.username

class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    author = db.relationship("User", backref='posts', lazy=True)

    def __repr__(self):
        return 'Blog post ' + str(self.id)

#--------------------------------------------------------------------------------------
#Forms

class RegistrationForm(FlaskForm):
    username = StringField("Username", validators=[Length(min=5, max=30), DataRequired()])
    email = StringField("Email", validators=[Email()])
    password = PasswordField("Password", validators=[Length(min=8), InputRequired()])
    password_confirm = PasswordField("Confirm Password", validators=[Length(min=8), EqualTo("password", message="Passwords must match")])

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError("Username already taken.")

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError("Email already taken.")


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[InputRequired()])

class CreateForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    content = TextAreaField("Content", validators=[DataRequired(), Length(min=30)])


#--------------------------------------------------------------------------------------
#Routes

@app.route('/user/<int:id>', methods=["GET", "POST"])
def index(id):
    user = User.query.get_or_404(id)
    form = CreateForm()
    if form.validate_on_submit():
        post = BlogPost.query.filter_by(title=form.title.data).first()
        if post:
            return redirect(url_for("index", id=user.id))
        new_post = BlogPost(title=form.title.data, content=form.content.data, author=user)
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("index", id=user.id))
    return render_template('index.html', form=form, user=user)

@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        new_user = User(username=form.username.data,
                        email=form.email.data,
                        password=form.password.data)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('posts'))
    return render_template("register.html", form=form, title="Sign Up")

@app.route("/login", methods= ['GET', "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('posts'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.password == form.password.data:
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for("posts"))
    return render_template("login.html", form=form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('posts'))

@app.route("/")
@app.route('/posts')
def posts():
    all_posts = BlogPost.query.order_by(BlogPost.date_posted).all()
    return render_template('posts.html', posts=all_posts)

@app.route('/posts/delete/<int:id>')
@login_required
def delete(id):
    post = BlogPost.query.get_or_404(id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    return redirect('/posts')

@app.route('/posts/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    form = CreateForm()
    post = BlogPost.query.get_or_404(id)
    if post.author != current_user:
        abort(403)
    form.title.data = post.title
    form.content.data = post.data

    if form.validate_on_submit():
        if form.content.data == post.content and form.title.data == post.title:
            return redirect(url_for("posts"))
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        return redirect(url_for("posts"))
    
    return render_template('create.html', post=post, form=form)


if __name__ == "__main__":
    manager.run()