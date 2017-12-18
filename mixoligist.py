
import os
from flask import Flask, render_template, session, redirect, request, url_for, flash
from flask_script import Manager, Shell
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FileField, PasswordField, BooleanField, SelectMultipleField, ValidationError
from wtforms.validators import Required, Length, Email, Regexp, EqualTo
from flask_sqlalchemy import SQLAlchemy
import random
from flask_migrate import Migrate, MigrateCommand

# Imports for email from app
from flask_mail import Mail, Message
from threading import Thread
from werkzeug import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

# Imports for login management
from flask_login import LoginManager, login_required, logout_user, login_user, UserMixin, current_user

# Configure base directory of app
basedir = os.path.abspath(os.path.dirname(__file__))

import requests
import json

app = Flask(__name__)
app.static_folder = 'static'
app.config['SECRET_KEY'] = 'hardtoguessstring'
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get('DATABASE_URL') or "postgresql://localhost/Mixoligist"  # TODO: decide what your new database name will be, and create it in postgresql, before running this new application
# Lines for db setup so it will work as expected
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

manager = Manager(app)
db = SQLAlchemy(app) # For database use
migrate = Migrate(app, db) # For database use/updating
manager.add_command('db', MigrateCommand) # Add migrate command to manager

login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'login'
login_manager.init_app(app)




### Helper Functions
def get_drinks(ingredients):
    base_url = 'http://www.thecocktaildb.com/api/json/v1/1/filter.php?i='
    search_string = ingredients[0].replace(' ','_')
    for i in ingredients[1:]:
        search_string = search_string + '&' + i.replace(' ','_')
    
    search_string = base_url + search_string
    drinks_dict = requests.get(search_string).json()
    
    drink_objects = []
    if len(drinks_dict['drinks']) > 0:
        for d in drinks_dict['drinks']:
            drink_obj = requests.get('http://www.thecocktaildb.com/api/json/v1/1/lookup.php?', params = {'i':d['idDrink']}).json()
            drink_objects.append(drink_obj)

    else:
        return "Sorry, there were no drinks found with those ingredients"
    

    return drink_objects

def get_drink_by_name(name):
    base_url = 'http://www.thecocktaildb.com/api/json/v1/1/search.php?s=' + name.replace(' ','_')
    drinks_dict = requests.get(base_url).json()
    d= drinks_dict['drinks'][0]
    ingredients = []
    ingr_str = 'strIngredient'
    for i in range(1,16):
        s = ingr_str + str(i)
        if d[s] != '':
            ingredients.append(d[s])
    return(d['strDrink'], ingredients, d['strInstructions'])




recipes = db.Table('recipes', db.Column('drink_id',db.Integer, db.ForeignKey('drinks.id')),
                              db.Column('ingredient_id',db.Integer,db.ForeignKey('ingredients.id')))


class User(UserMixin,db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255),unique = True, index = True)
    email = db.Column(db.String(255),unique = True, index = True)
    
    password_hash = db.Column(db.String(128))

    @property
    def password(self):
        raise AttributeError('cannot read password')

    @password.setter
    def password(self,password):
        self.password_hash = generate_password_hash(password)
    
    def verify_password(self,password):
        return check_password_hash(self.password_hash,password)

class Drink(db.Model):
    __tablename__ = 'drinks'
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(255))
    instructions = db.Column(db.String(500))
    ingredients = db.relationship('Ingredient', secondary=recipes,
                                       backref=db.backref('ingredients', lazy='dynamic'), lazy='dynamic')

class Ingredient(db.Model):
    __tablename__ = 'ingredients'
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(255))

class Favorite_Drink(db.Model):
    __tablename__ = 'favorite_drinks'
    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer)
    drink_id = db.Column(db.Integer)

## DB load functions
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id)) # returns User object or None


class RegistrationForm(FlaskForm):
    email = StringField('Email:', validators=[Required(),Length(1,64),Email()])
    username = StringField('Username:',validators=[Required(),Length(1,64),Regexp('^[A-Za-z][A-Za-z0-9_.]*$',0,'Usernames must have only letters, numbers, dots or underscores')])
    password = PasswordField('Password:',validators=[Required(),EqualTo('password2',message="Passwords must match")])
    password2 = PasswordField("Confirm Password:",validators=[Required()])
    submit = SubmitField('Register User')

    #Additional checking methods for the form
    def validate_email(self,field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

    def validate_username(self,field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already taken')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[Required(), Length(1,64), Email()])
    password = PasswordField('Password', validators=[Required()])
    remember_me = BooleanField('Keep me logged in')
    submit = SubmitField('Log In')


class MixyForm(FlaskForm):
    ingredients = StringField("Find new recipes by typing in a few of your favorite ingredients")
    submit = SubmitField('Submit')

class add_drink_form(FlaskForm):
    name = StringField("Enter the Drink name you wish to add")
    submit = SubmitField('Submit')

class custom_drink_form(FlaskForm):
    name = StringField("What do you call it?")
    ingredients = StringField("What are the ingredients? Please separate ingredients by a comma and a space")
    instructions = StringField("How do you make it?")
    submit = SubmitField('Submit')



## get or create functions
def get_or_create_drink(db_session,drink):
    drinks = Drink.query.all()
    for drnk in drinks:
        if drnk.name == drink[0]:
            return drnk
    drnk = Drink(name = drink[0], instructions = drink[2], ingredients = [])
    ingredients = drink[1]
    i_objects = []
    
    
    for i in ingredients:
        check = Ingredient.query.filter_by(name = i).first()
        if check:
            drnk.ingredients.append(check)
        else:

            new = Ingredient(name = i)
            drnk.ingredients.append(new)
    db_session.add(drnk)
    db_session.commit()
    return drnk



    
def get_or_create_favorite(db_session,user_id,drink_id):
    favorites = Favorite_Drink.query.all()
    for favorite in favorites:
        if (favorite.user_id == user_id) and (favorite.drink_id == drink_id):
            return favorite
    favorite = Favorite_Drink(user_id = user_id, drink_id = drink_id)
    db_session.add(favorite)
    db_session.commit()
    return favorite


## Login routes
@app.route('/login',methods=["GET","POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            return redirect(request.args.get('next') or url_for('index'))
        flash('Invalid username or password.')
    return render_template('login.html',form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out')
    return redirect(url_for('index'))

@app.route('/register',methods=["GET","POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data,username=form.username.data,password=form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('You can now log in!')
        return redirect(url_for('login'))
    return render_template('register.html',form=form)

@app.route('/secret')
@login_required
def secret():
    return "Only authenticated users can do this! Try to log in or contact the site admin."


@app.route('/', methods = ["GET", "POST"])
def index():
    drinks = Drink.query.all()

    form = MixyForm()
   

    if request.method == 'POST':
        
        ingredients = form.ingredients.data
        ingredients = ingredients.split(', ')
        drinks = get_drinks(ingredients)
        
        drink_tuples = []
        for d in drinks:

            drnk = d['drinks'][0]
            ingredients = []
            ingr_str = 'strIngredient'
            for i in range(1,16):
                s = ingr_str + str(i)
                if (drnk[s] != '') and (drnk[s] != None):
                    ingredients.append(drnk[s])
            drink_tuples.append((drnk['strDrink'], ingredients, drnk['strInstructions']))

        
        
        
        return render_template('drinks.html', drinks = drink_tuples)

        
        #return redirect(url_for('all_drinks'))
    return render_template('index.html', form = form)
@app.route('/user_drinks')
def user_drinks():
    drinks = Drink.query.all()
    user_drinks = Favorite_Drink.query.filter_by(user_id = current_user.id).all()
    user_drinks = [drink.drink_id for drink in user_drinks]
    drinks = [drink for drink in drinks if drink.id in user_drinks]
    drink_list = []
    for drink in drinks:
        ingredients = drink.ingredients.all()
        ingredients = [ingredient.name for ingredient in ingredients if ingredient.name != None]
        drink_list.append((drink.name,ingredients,drink.instructions))

    

    return render_template('user_drinks.html',drinks = drink_list)

@app.route('/add_drink',methods = ['GET', 'POST'])
def add_drink():
    form = add_drink_form()
    if request.method == 'POST':
        new_drink = (get_or_create_drink(db.session,get_drink_by_name(form.name.data)))
        f = get_or_create_favorite(db.session,current_user.id,new_drink.id)
       
        return redirect(url_for('user_drinks'))
    return render_template('add_drink.html', form = form)




@app.route('/all_drinks')
def all_drinks():
    
    drinks = Drink.query.all()
   

    drink_list = []
    for drink in drinks:
        ingredients = drink.ingredients.all()
        ingredients = [ingredient.name for ingredient in ingredients if ingredient.name != None]
        drink_list.append((drink.name,ingredients,drink.instructions))
    return render_template('all_drinks.html',drinks = drink_list)


@app.route('/custom_drink', methods = ['GET','POST'])
def custom_drink():
    form = custom_drink_form()
    if request.method == 'POST':
        ingredients = form.ingredients.data.split(', ')
        drnk = get_or_create_drink(db.session,(form.name.data, ingredients, form.instructions.data))
        f = get_or_create_favorite(db.session,user_id = current_user.id, drink_id = drnk.id)
        return redirect(url_for('user_drinks'))
    return render_template('custom_drink.html', form = form)

@app.errorhandler(404)
def page_not_found(e):
    return "page_not_found"

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500



if __name__ == '__main__':
    db.create_all()
    manager.run()
