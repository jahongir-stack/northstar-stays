from flask import Flask,render_template,request,session,redirect,url_for,flash,abort
from werkzeug.security import generate_password_hash,check_password_hash
from functools import wraps
from pathlib import Path
import os,sqlite3
app=Flask(__name__)
app.secret_key=os.getenv('SECRET_KEY','local-development-only')
DB=Path(__file__).parent/'instance'/'app.db'
DB.parent.mkdir(exist_ok=True)
def connect():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;return c
def login_required(fn):
 @wraps(fn)
 def wrapped(*args,**kwargs):
  if 'user' not in session:return redirect(url_for('login'))
  return fn(*args,**kwargs)
 return wrapped
@app.route('/login',methods=['GET','POST'])
def login():
 if request.method=='POST':
  email=request.form.get('email','').strip().lower();pw=request.form.get('password','')
  with connect() as c:
   if request.form.get('action')=='register':
    if len(pw)<8 or not email:flash('Use a valid email and 8+ character password.');return redirect(url_for('login'))
    try:c.execute('INSERT INTO users(email,password) VALUES(?,?)',(email,generate_password_hash(pw)))
    except sqlite3.IntegrityError:flash('Account exists.');return redirect(url_for('login'))
   row=c.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
   if row and check_password_hash(row['password'],pw):session.clear();session['user']=row['id'];return redirect(url_for('index'))
  flash('Invalid credentials.')
 return render_template('login.html')
@app.route('/logout',methods=['POST'])
def logout():session.clear();return redirect(url_for('index'))

def init_db():
 with connect() as c:
  c.executescript("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,email TEXT UNIQUE NOT NULL,password TEXT NOT NULL); CREATE TABLE IF NOT EXISTS rooms(id INTEGER PRIMARY KEY,name TEXT,price INTEGER,category TEXT); CREATE TABLE IF NOT EXISTS bookings(id INTEGER PRIMARY KEY,user_id INTEGER,room_id INTEGER,checkin TEXT,checkout TEXT);")
  if not c.execute("SELECT 1 FROM rooms LIMIT 1").fetchone():c.execute("INSERT INTO rooms(name,price,category) VALUES ('Skyline Suite',240,'Suite'),('Coastal King',165,'Deluxe'),('Garden Retreat',195,'Premium'),('City Studio',120,'Studio')")
@app.route('/')
def index():
 with connect() as c:
  rooms=c.execute('SELECT * FROM rooms').fetchall();return render_template('index.html',items=rooms)
@app.route('/book/<int:item>',methods=['POST'])
@login_required
def book(item):
 from datetime import date
 start=request.form.get('start','');end=request.form.get('end','')
 try:
  valid=date.fromisoformat(start)>=date.today() and date.fromisoformat(end)>date.fromisoformat(start)
 except ValueError:valid=False
 if not valid:flash('Select valid future dates.');return redirect(url_for('index'))
 with connect() as c:
  if not c.execute('SELECT 1 FROM rooms WHERE id=?',(item,)).fetchone():abort(404)
  conflict=c.execute('SELECT 1 FROM bookings WHERE room_id=? AND checkin<? AND checkout>?',(item,end,start)).fetchone()
  if conflict:flash('Room unavailable for these dates.')
  else:c.execute('INSERT INTO bookings(user_id,room_id,checkin,checkout) VALUES(?,?,?,?)',(session['user'],item,start,end));flash('Reservation created!')
 return redirect(url_for('index'))

if __name__=='__main__':
 init_db()
 app.run(debug=os.getenv('FLASK_DEBUG')=='1')
