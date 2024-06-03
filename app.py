from flask import Flask, render_template, request, redirect, url_for, session, g
import random
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

DATABASE = 'leaderboard.db'


# Database helper functions
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leaderboard (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name TEXT NOT NULL,
                score INTEGER NOT NULL,
                total_time INTEGER NOT NULL,
                average_time REAL NOT NULL
            )
        ''')
        db.commit()


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def add_to_leaderboard(player_name, score, total_time, average_time):
    db = get_db()
    db.execute('INSERT INTO leaderboard (player_name, score, total_time, average_time) VALUES (?, ?, ?, ?)',
               [player_name, score, total_time, average_time])
    db.commit()


def get_leaderboard():
    return query_db('SELECT player_name, score, total_time, average_time FROM leaderboard ORDER BY score DESC')


# Game operations
def add(num1, num2):
    return num1 + num2


def mul(num1, num2):
    return num1 * num2


def div(num1, num2):
    return num1 // num2


def sub(num1, num2):
    return num1 - num2


operations = {'-': sub, '/': div, '*': mul, '+': add}


def generate_question(level):
    if level == 'easy':
        num1 = random.randint(1, 10)
        num2 = random.randint(1, 10)
    elif level == 'hard':
        num1 = random.randint(10, 30)
        num2 = random.randint(10, 30)
    op = random.choice(list(operations.keys()))
    return num1, num2, op


@app.route('/')
def index():
    session.clear()
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start():
    print(request.form)  # Debugging: Print the form data
    player_name = request.form.get('player_name')
    level = request.form.get('level')
    
    if not player_name or not level:
        return "Missing player name or level", 400
    
    session['player_name'] = player_name
    session['level'] = level
    session['score'] = 0
    session['questions_answered'] = 0
    num1, num2, op = generate_question(level)
    session['num1'] = num1
    session['num2'] = num2
    session['op'] = op
    session['timeleft'] = 30
    return redirect(url_for('game'))


@app.route('/game')
def game():
    if 'player_name' not in session:
        return redirect(url_for('index'))
    return render_template('game.html',
                           player_name=session['player_name'],
                           score=session['score'],
                           timeleft=session['timeleft'],
                           num1=session['num1'],
                           num2=session['num2'],
                           op=session['op'])

@app.route('/submit', methods=['POST'])
def submit():
    if 'player_name' not in session:
        return redirect(url_for('index'))

    try:
        answer = int(request.form['answer'])
    except ValueError:
        answer = None

    num1 = session['num1']
    num2 = session['num2']
    op = session['op']
    correct_answer = operations[op](num1, num2)

    if answer == correct_answer:
        session['score'] += 1
    else:
        session['score'] -= 1

    session['questions_answered'] += 1
    session['timeleft'] = int(request.form['timeleft'])

    if session['timeleft'] <= 0:
        total_time = 30
        average_time = total_time / session['questions_answered'] if session['questions_answered'] > 0 else 0
        player_name = session['player_name']

        add_to_leaderboard(player_name, session['score'], total_time, average_time)

        return redirect(url_for('leaderboard'))

    num1, num2, op = generate_question(session['level'])
    session['num1'] = num1
    session['num2'] = num2
    session['op'] = op

    return redirect(url_for('game'))



@app.route('/leaderboard')
def leaderboard():
    sorted_leaderboard = get_leaderboard()
    return render_template('leaderboard.html', leaderboard=sorted_leaderboard)


if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        init_db()
    app.run(debug=True)
