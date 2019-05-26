from flask import Flask, render_template, abort, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
from flask_restful import Api, Resource 

from datetime import datetime
import os 


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'yekterces'

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

api = Api(app)


class Conference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    ticket_cost = db.Column(db.Float, nullable=False)
    attendees = db.relationship('ConferenceBarrelUser', secondary='conference_barrel_ticket')

    def __repr__(self):
        return '<Conference {}>'.format(self.title)


class ConferenceBarrelUser(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(128), nullable=False)
    password = db.Column(db.String(128), nullable=False)
    conferences = db.relationship('Conference', secondary='conference_barrel_ticket')

    def __init__(self, username, password):
        self.username = username
        self.password = password 


class ConferenceBarrelTicket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('conference_barrel_user.id'))
    conference_id = db.Column(db.Integer, db.ForeignKey('conference.id'))
    user = db.relationship(ConferenceBarrelUser, backref=db.backref('tickets', lazy='dynamic'))
    conference = db.relationship(Conference, backref=db.backref('tickets', lazy='dynamic'))


@app.route('/')
@app.route('/index') 
def index():
    return render_template('index.html')


@app.route('/about')
def about():
    return 'About Conference Barrel'


@app.route('/conferences')
@app.route('/conferences/<int:conference_id>')
def conferences(conference_id=None):
    if conference_id is not None:
        conference = Conference.query.get(conference_id)
        if conference is None:
            abort(404)
        return render_template('details.html', conference=conference)
    else:
        return render_template('conferences.html', conferences=Conference.query.all())


@app.route('/conferences/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        title = request.form['title']
        date = request.form['date']
        ticket_cost = request.form['ticket_cost']

        conference = Conference(title=title, date=datetime.strptime(date, '%Y-%m-%d'), ticket_cost=float(ticket_cost))
        db.session.add(conference)
        db.session.commit()

        return redirect(url_for('conferences'))
    else:
        return render_template('add.html')


@app.errorhandler(404) 
def handle_404(e):
    return render_template('404.html'), 404


@app.errorhandler(401)
def handle_401(e):
    return redirect(url_for('login'))


@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        needle = request.form['needle']
        results = Conference.query.filter(Conference.title.like('%{}%'.format(needle))).all()
        return render_template('results.html', results=results)
    else:
        return render_template('search.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        u = ConferenceBarrelUser.query.filter(ConferenceBarrelUser.username == username).filter(ConferenceBarrelUser.password == password).first()
        if u is None:
            flash('Invalid username and/or password')
            return abort(401)
        login_user(u)
        return redirect(url_for('secret_data'))
    else:
        return render_template('login.html')


@app.route('/secret_data')
@login_required
def secret_data():
    return render_template('secret_data.html')


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


@login_manager.user_loader
def load_user(id):
    return ConferenceBarrelUser.query.get(id)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password1 = request.form['password1']
        password2 = request.form['password2']

        u = ConferenceBarrelUser.query.filter(ConferenceBarrelUser.username == username).first()
        password_match = password1 == password2

        if u is not None:
            flash('Username already exists')
            return redirect(url_for('register'))

        if password_match is False:
            flash('Passwords did not match')
            return redirect(url_for('register'))

        u = ConferenceBarrelUser(username, password1)
        db.session.add(u)
        db.session.commit()

        return redirect(url_for('login'))
    else:
        return render_template('register.html')


@app.route('/new_ticket/<int:conference_id>')
@login_required
def new_ticket(conference_id):
    conference = Conference.query.get(conference_id)
    ticket = ConferenceBarrelTicket(user=current_user, conference=conference)
    db.session.add(ticket)
    db.session.commit()
    return redirect(url_for('profile'))


@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')


class ConferenceResource(Resource):
    def get(self, conference_id=None):
        if conference_id is None:
            return [
                {
                    'id': conference.id,
                    'title': conference.title 
                }
                for conference in Conference.query.all()
            ]
        else:
            conference = Conference.query.get(conference_id)
            return {
                'id': conference.id,
                'title': conference.title,
                'date': conference.date.strftime('%m/%d/%Y'),
                'ticket_cost': conference.ticket_cost,
                'attendee_count': len(conference.tickets.all())
            }


api.add_resource(ConferenceResource, '/api/conferences', '/api/conferences/<int:conference_id>')
