from datetime import date
from flask import Flask, abort, request, render_template, redirect, url_for, flash, session
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
# Import your forms from the forms.py
from forms import CreatePostForm, LoginForm, RegisterForm
from dotenv import load_dotenv
import os


load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
ckeditor = CKEditor(app)
login_manager = LoginManager()
Bootstrap5(app)

# TODO: Configure Flask-Login


# CREATE DATABASE
class Base(DeclarativeBase):
    pass
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
db = SQLAlchemy(model_class=Base)
login_manager.init_app(app)
db.init_app(app)



#Create User 

class User(db.Model, UserMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(1000))

    posts = relationship("BlogPost", back_populates="author" )


# CONFIGURE TABLES
class BlogPost(db.Model):
    __tablename__ = "posts"

     # Create Foreign Key, "users.id" the users refers to the tablename of User.

    author_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("users.id"))

    # Create reference to the User object. The "posts" refers to the posts property in the User class.

    author = relationship("User", back_populates="posts")

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)





# create a user loader callback 
@login_manager.user_loader
def load_user(id):
    with db.session() as session:
     return session.get(User, int(id))

def admin_only(f):
    @wraps(f)  # ✅ Preserves function metadata
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.id != 1:
            abort(403)  # ❌ Access denied
        return f(*args, **kwargs)  # ✅ Allow access
    return decorated





with app.app_context():
    db.create_all()


# TODO: Use Werkzeug to hash the user's password when creating a new user.
@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    login_form = LoginForm()

    if request.method == "POST":
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        if not name or not email or not password:
            flash("All fields are required", "danger")
            return redirect(url_for('register'))  # Redirect instead of returning raw text
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("User already exists. Please log in.", "warning")
            return redirect(url_for('login'))
        
        # Hash password and create new user
        hashed_pass = generate_password_hash(password, method='scrypt', salt_length=8)
        new_user = User(name=name, email=email, password=hashed_pass)

        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)

        session['name'] = name  # Store name in session
        return render_template("index.html", name=name)  # Redirect instead of rendering `index.html` directly

    return render_template("register.html", form=form)



# TODO: Retrieve a user from the database based on their email. 
@app.route('/login', methods=['GET','POST'])
def login():

    form = LoginForm()
    if request.method == "POST":
        email = request.form.get('email')
        password= request.form.get("password")

        user = User.query.filter_by(email=email).first()

        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))

        elif not check_password_hash(user.password, password):
            flash('Password incorrect, please try again.')
            return redirect(url_for('login'))
        else:
            login_user(user)

            return redirect(url_for("get_all_posts"))
            
        
    return render_template("login.html", form=form)



@app.route('/logout')

def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route('/')
def get_all_posts():

    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


# TODO: Allow logged-in users to comment on posts
@app.route("/post/<int:post_id>")
def show_post(post_id):
    requested_post = db.get_or_404(BlogPost, post_id)
    return render_template("post.html", post=requested_post)


# TODO: Use a decorator so only an admin user can create a new post
@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author_id=current_user.id,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


# TODO: Use a decorator so only an admin user can edit a post
@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
    title=post.title,
    subtitle=post.subtitle,
    img_url=post.img_url,
    author_id=post.author_id,  # ✅ CORRECT (author_id is an integer)
    body=post.body
)
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author_id = current_user.id
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True)


# TODO: Use a decorator so only an admin user can delete a post

@app.route("/delete/<int:post_id>")
@admin_only
@login_required
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


if __name__ == "__main__":
    app.run(debug=True, port=5002)
