from flask import Flask, render_template, url_for, request, redirect, session, make_response
from functools import wraps
from database import session as db
from models import User, Item, Purchase, ActivationToken, PasswordToken
from security import Authentication, Email
app = Flask(__name__)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'email' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function              

def group_required(groups):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            
            user = User.get(session['email'])
            authorized = False

            for membership in user.memberships:
                if membership.group.name in groups:
                    authorized = True

            if not authorized:
                return redirect(url_for('home'))
            else:
                return f(*args, **kwargs)

        return decorated_function
    return decorator


def get_urls():
    return [
        ('Home',url_for('home')),
        ('Buy',url_for('buy')),
        ('History',url_for('history')),
        ('Logout',url_for('logout')),
    ]


@app.route('/')
@login_required
def home():
    data = {}
    data['nav_urls'] = get_urls()
    data['active_url'] = url_for('home')
    return render_template('index.html', data=data)


@app.route('/login/', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        user = User.get(request.form['email'])
        if user != None and Authentication.authenticate(user, request.form['password']):
             session['email'] = request.form['email']
             session.permanent = True
             return redirect(url_for('home'))
        else:
            return redirect(url_for('login'))
    else:
        return render_template('login.html', urls=get_urls())


@app.route('/logout/')
def logout():
    session.pop('email', None)
    return redirect(url_for('login'))


@app.route('/register/', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        if User.get(request.form['email']) == None:
            
            user = User(request.form['email'], request.form['password'])
            db.add(user)
            db.commit()

            token = ActivationToken(user)
            db.add(token)
            db.commit()

            activation_url = url_for('activate', url_part=token.url_part)
            email_body = render_template('email/register.html', activation_url=activation_url)
            #Email.send()
            return email_body

            return token.url_part
        else:
            return 'Already exists.'
    else:
        return render_template('register.html', urls=get_urls())


@app.route('/user/activate/<url_part>')
def activate(url_part):

    token = ActivationToken.query.filter(ActivationToken.url_part==url_part).first()
    
    if token != None:
        user = token.user
        user.activated = True
        db.add(user)
        db.commit()

        return redirect(url_for('login'))
    else:
        return 'Failure'

@app.route('/buy/', methods=['GET','POST'])
@login_required
def buy():
    if request.method == 'POST':
        user = User.get(session['email'])
        item = Item.query.filter(Item.id==request.form['item_id']).first()
        purchase = Purchase(user, item)
        db.add(purchase)
        db.commit()
        return redirect(url_for('history'))
    else:
        data = {}
        data['nav_urls'] = get_urls()
        data['active_url'] = url_for('buy')

        data['items'] = Item.query.all()
        response = make_response(render_template('buy.html', data=data))
        response.headers['Cache-Control'] = 'no-cache'
        return response


@app.route('/history/')
@login_required
def history():
    data = {}
    data['nav_urls'] = get_urls()
    data['active_url'] = url_for('history')
    user = User.get(session['email'])
    purchases = Purchase.query.filter(Purchase.user_id==user.id).order_by(Purchase.timestamp.desc())
    data['purchases'] = purchases
    return render_template('history.html', data=data)


@app.route('/admin/')
@login_required
@group_required(['admin'])
def admin():
    return 'You are an admin.'


@app.teardown_appcontext
def shutdown_session(exception=None):
    db.remove()


if __name__ == '__main__':
    app.secret_key = 'Development secret key'
    app.run(debug=True, host='0.0.0.0')
