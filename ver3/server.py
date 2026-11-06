#!/usr/bin/env python3
"""LINGAP local demonstration server (Python 3.10+, no external packages)."""
import base64
import csv
import hashlib
import hmac
import io
import json
import os
import re
import secrets
import sqlite3
import threading
from datetime import date, datetime, timedelta
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
UPLOADS = ROOT / 'uploads'
DB = DATA / 'lingap.sqlite3'
for p in [DATA, UPLOADS]: p.mkdir(exist_ok=True)
HOST = os.getenv('LINGAP_HOST', '127.0.0.1')
PORT = int(os.getenv('LINGAP_PORT', '8000'))
ADMIN_USER = os.getenv('LINGAP_ADMIN_USER', 'admin')
ADMIN_PASS = os.getenv('LINGAP_ADMIN_PASSWORD', 'ChangeMe123!')
SESSIONS = {}
CLIENT_SESSIONS = {}
LOCK = threading.Lock()
ALLOWED_STATUSES = ['Received', 'For screening', 'Needs information', 'For appointment', 'For lawyer review', 'Accepted', 'Declined', 'Closed']
LAWYERS = [
 ('Atty. Maria L. Dela Peña','Family Law / VAWC','team leader'),
 ('Atty. Jose P. Santos','Labor Law',''),
 ('Atty. Anthony V. Reyes','Civil Law / Small Claims',''),
 ('Atty. Regina M. Cruz','Criminal Law','team leader'),
 ('Atty. Carmen S. Villanueva','Family Law / VAWC',''),
]

def now(): return datetime.now().isoformat(timespec='seconds')
def conn():
 c = sqlite3.connect(DB, timeout=20)
 c.row_factory = sqlite3.Row
 c.execute('PRAGMA foreign_keys=ON')
 return c

def init_db():
 with conn() as db:
  db.executescript('''
  CREATE TABLE IF NOT EXISTS clients (
   id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
   salt TEXT NOT NULL, password_hash TEXT NOT NULL, created_at TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS matters (
   id INTEGER PRIMARY KEY AUTOINCREMENT, reference TEXT UNIQUE NOT NULL,
   name TEXT NOT NULL, email TEXT NOT NULL, phone TEXT, city TEXT,
   language TEXT, assistance TEXT, household_size INTEGER, monthly_income REAL,
   category TEXT, summary TEXT, screening TEXT, status TEXT DEFAULT 'Received',
   priority TEXT DEFAULT 'Normal', assigned_to TEXT DEFAULT '', consent_at TEXT NOT NULL,
   created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS appointments (
   id INTEGER PRIMARY KEY AUTOINCREMENT, matter_id INTEGER NOT NULL REFERENCES matters(id),
   date TEXT NOT NULL, time TEXT NOT NULL, type TEXT NOT NULL,
   created_at TEXT NOT NULL, UNIQUE(date,time));
  CREATE TABLE IF NOT EXISTS documents (
   id INTEGER PRIMARY KEY AUTOINCREMENT, matter_id INTEGER NOT NULL REFERENCES matters(id),
   filename TEXT NOT NULL, stored_name TEXT NOT NULL, size INTEGER NOT NULL, created_at TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS notifications (
   id INTEGER PRIMARY KEY AUTOINCREMENT, recipient TEXT NOT NULL, subject TEXT NOT NULL,
   message TEXT NOT NULL, kind TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Demo only — not sent',
   created_at TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS events (
   id INTEGER PRIMARY KEY AUTOINCREMENT, matter_id INTEGER NOT NULL REFERENCES matters(id),
   label TEXT NOT NULL, created_at TEXT NOT NULL);
  ''')
  cols={r[1] for r in db.execute('PRAGMA table_info(matters)')}
  if 'client_id' not in cols: db.execute('ALTER TABLE matters ADD COLUMN client_id INTEGER REFERENCES clients(id)')
  if db.execute('SELECT COUNT(*) FROM matters').fetchone()[0] == 0:
   samples = [
    ('Alex Reyes','alex.demo@example.test','Family Law / VAWC','For screening','High','Atty. Maria L. Dela Peña'),
    ('Jamie Santos','jamie.demo@example.test','Labor Law','Accepted','Normal','Atty. Jose P. Santos'),
    ('Taylor Cruz','taylor.demo@example.test','Civil Law / Small Claims','For lawyer review','Normal','Atty. Anthony V. Reyes'),
    ('Casey Ramos','casey.demo@example.test','Criminal Law','Needs information','High',''),
    ('Robin Garcia','robin.demo@example.test','Land / Housing','For appointment','Normal',''),
    ('Sam Villanueva','sam.demo@example.test','Family Law / VAWC','Closed','Normal','Atty. Carmen S. Villanueva'),
    ('Drew Mendoza','drew.demo@example.test','Labor Law','Declined','Normal',''),
    ('Pat Flores','pat.demo@example.test','Other','Received','Normal',''),
   ]
   for i,(name,email,category,status,priority,lawyer) in enumerate(samples):
    ts=(datetime.now()-timedelta(days=i*2)).isoformat(timespec='seconds')
    ref=f'OLA-DEMO-{i+1:04}'
    db.execute('''INSERT INTO matters(reference,name,email,phone,city,language,assistance,household_size,monthly_income,category,summary,screening,status,priority,assigned_to,consent_at,created_at,updated_at)
       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
       (ref,name,email,'','Metro Manila','en','representation',3,9000,category,'SYNTHETIC DEMO DATA ONLY','Needs human review',status,priority,lawyer,ts,ts,ts))
  db.commit()

def send_notice(db, recipient, kind, subject, message):
 db.execute('INSERT INTO notifications(recipient,kind,subject,message,created_at) VALUES (?,?,?,?,?)',
            (recipient,kind,subject,message,now()))

def json_body(handler):
 length=int(handler.headers.get('Content-Length','0'))
 if length > 6_000_000: raise ValueError('Request is too large.')
 if not length: return {}
 return json.loads(handler.rfile.read(length).decode('utf-8'))

def clean(s, maxlen=200): return str(s or '').strip()[:maxlen]
def is_email(v): return bool(re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',v))
def admin_ok(h):
 c=cookies.SimpleCookie()
 try: c.load(h.headers.get('Cookie',''))
 except cookies.CookieError: return False
 token=c['lingap_session'].value if 'lingap_session' in c else ''
 return bool(token and token in SESSIONS)

def client_id(h):
 c=cookies.SimpleCookie()
 try:c.load(h.headers.get('Cookie',''))
 except cookies.CookieError:return None
 token=c['lingap_client'].value if 'lingap_client' in c else ''
 return CLIENT_SESSIONS.get(token)

def password_hash(password,salt):
 return hashlib.pbkdf2_hmac('sha256',password.encode('utf-8'),bytes.fromhex(salt),260000).hex()

def client_cookie(token,max_age=28800):
 return f'lingap_client={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={max_age}'

class App(BaseHTTPRequestHandler):
 server_version='LINGAPDemo/1.0'
 def log_message(self,fmt,*args): print('[HTTP]',fmt % args)
 def send_headers(self,status=200,ctype='application/json; charset=utf-8',extras=None):
  self.send_response(status)
  self.send_header('Content-Type',ctype)
  self.send_header('Cache-Control','no-store')
  self.send_header('X-Content-Type-Options','nosniff')
  self.send_header('X-Frame-Options','DENY')
  self.send_header('Referrer-Policy','no-referrer')
  if extras:
   for k,v in extras.items(): self.send_header(k,v)
  self.end_headers()
 def reply(self,obj,status=200,extras=None):
  raw=json.dumps(obj,ensure_ascii=False).encode('utf-8')
  self.send_headers(status,extras=extras)
  self.wfile.write(raw)
 def fail(self,msg,status=400): self.reply({'error':msg},status)
 def require_admin(self):
  if not admin_ok(self): self.fail('Admin sign-in required.',401);return False
  return True
 def do_GET(self):
  try: self.get()
  except Exception as exc:
   print('GET error:',repr(exc));self.fail('Unexpected server error.',500)
 def get(self):
  parsed=urlparse(self.path);path=parsed.path;q=parse_qs(parsed.query)
  if path in ('/','/index.html'):
   b=(ROOT/'static'/'index.html').read_bytes();self.send_headers(200,'text/html; charset=utf-8');self.wfile.write(b);return
  if path.startswith('/static/'):
   name=path.removeprefix('/static/')
   if name not in ('app.js','style.css','favicon.svg'): return self.fail('Not found.',404)
   types={'app.js':'text/javascript; charset=utf-8','style.css':'text/css; charset=utf-8','favicon.svg':'image/svg+xml'}
   b=(ROOT/'static'/name).read_bytes();self.send_headers(200,types[name]);self.wfile.write(b);return
  if path=='/api/health': return self.reply({'ok':True,'mode':'local-demo'})
  if path=='/api/slots':
   day=clean(q.get('date',[''])[0],10)
   try: dt=date.fromisoformat(day)
   except ValueError: return self.fail('Select a valid date.')
   if dt < date.today() or dt > date.today()+timedelta(days=60) or dt.weekday()>=5:
    return self.reply({'slots':[]})
   with conn() as db:
    used={r[0] for r in db.execute('SELECT time FROM appointments WHERE date=?',(day,))}
   return self.reply({'slots':[s for s in ['09:00','10:00','11:00','13:00','14:00','15:00'] if s not in used]})
  if path=='/api/status':
   ref=clean(q.get('ref',[''])[0],30).upper();email=clean(q.get('email',[''])[0],200).lower()
   with conn() as db:
    r=db.execute('SELECT id,reference,name,category,screening,status,created_at,updated_at FROM matters WHERE reference=? AND lower(email)=?',(ref,email)).fetchone()
    if not r: return self.fail('No matching application found.',404)
    appointment=db.execute('SELECT date,time,type FROM appointments WHERE matter_id=?',(r['id'],)).fetchone()
    events=db.execute('SELECT label,created_at FROM events WHERE matter_id=? ORDER BY id DESC',(r['id'],)).fetchall()
   return self.reply({'matter':dict(r),'appointment':dict(appointment) if appointment else None,'events':[dict(x) for x in events]})
  if path=='/api/client/me':
   cid=client_id(self)
   if not cid:return self.reply({'authenticated':False})
   with conn() as db:
    r=db.execute('SELECT id,name,email FROM clients WHERE id=?',(cid,)).fetchone()
   return self.reply({'authenticated':bool(r),'client':dict(r) if r else None})
  if path=='/api/client/matters':
   cid=client_id(self)
   if not cid:return self.fail('Please sign in.',401)
   with conn() as db:
    rows=db.execute("""SELECT id,reference,category,screening,status,assigned_to,created_at,updated_at
     FROM matters WHERE client_id=? ORDER BY created_at DESC""",(cid,)).fetchall()
    results=[]
    for r in rows:
     a=db.execute('SELECT date,time,type FROM appointments WHERE matter_id=?',(r['id'],)).fetchone()
     events=db.execute('SELECT label,created_at FROM events WHERE matter_id=? ORDER BY id DESC',(r['id'],)).fetchall()
     results.append({'matter':dict(r),'appointment':dict(a) if a else None,'events':[dict(e) for e in events]})
   return self.reply({'matters':results})
  if path=='/api/admin/me':return self.reply({'authenticated':admin_ok(self)})
  if path.startswith('/api/admin/'):
   if not self.require_admin(): return
   with conn() as db:
    if path=='/api/admin/summary':
     counts={r['status']:r['total'] for r in db.execute('SELECT status,COUNT(*) total FROM matters GROUP BY status')}
     categories=[dict(r) for r in db.execute('SELECT category,COUNT(*) total FROM matters GROUP BY category ORDER BY total DESC')]
     byday=[dict(r) for r in db.execute('SELECT substr(created_at,1,10) day, COUNT(*) total FROM matters GROUP BY day ORDER BY day DESC LIMIT 14')]
     return self.reply({'total':sum(counts.values()),'counts':counts,'categories':categories,'byday':list(reversed(byday)),'appointments':db.execute('SELECT COUNT(*) FROM appointments').fetchone()[0], 'prescreened':db.execute("SELECT COUNT(*) FROM matters WHERE screening != ''").fetchone()[0]})
    if path=='/api/admin/matters':
     rows=db.execute('SELECT m.*,a.date appointment_date,a.time appointment_time FROM matters m LEFT JOIN appointments a ON a.matter_id=m.id ORDER BY m.created_at DESC').fetchall()
     return self.reply({'matters':[dict(r) for r in rows]})
    if path=='/api/admin/notifications':
     return self.reply({'notifications':[dict(r) for r in db.execute('SELECT * FROM notifications ORDER BY id DESC LIMIT 150')]})
    if path=='/api/admin/lawyers':return self.reply({'lawyers':[{'name':a,'specialization':b,'role':c,'caseload':db.execute('SELECT COUNT(*) FROM matters WHERE assigned_to=? AND status NOT IN ("Closed","Declined")',(a,)).fetchone()[0]} for a,b,c in LAWYERS]})
    if path=='/api/admin/export.csv':
     buff=io.StringIO();writer=csv.writer(buff);writer.writerow(['Reference','Date','Category','Screening','Status','Priority','Assigned'])
     for r in db.execute('SELECT reference,created_at,category,screening,status,priority,assigned_to FROM matters'):
      writer.writerow([str(v) if not str(v).startswith(('=','+','-','@')) else "'"+str(v) for v in r])
     self.send_headers(200,'text/csv; charset=utf-8',{'Content-Disposition':'attachment; filename="lingap-demo-report.csv"'})
     self.wfile.write(buff.getvalue().encode('utf-8'));return
  self.fail('Not found.',404)
 def do_POST(self):
  try:
   body=json_body(self);self.post(urlparse(self.path).path,body)
  except (ValueError,json.JSONDecodeError) as e:self.fail(str(e))
  except Exception as e:print('POST error:',repr(e));self.fail('Unexpected server error.',500)
 def post(self,path,b):
  if path=='/api/client/register':
   name=clean(b.get('name'),120);email=clean(b.get('email'),200).lower();password=str(b.get('password',''))
   if len(name)<2 or not is_email(email):return self.fail('Enter a name and valid email.')
   if len(password)<10 or len(password)>128:return self.fail('Password must be 10–128 characters.')
   salt=secrets.token_hex(16);digest=password_hash(password,salt)
   with conn() as db:
    try:
     cur=db.execute('INSERT INTO clients(name,email,salt,password_hash,created_at) VALUES(?,?,?,?,?)',(name,email,salt,digest,now()))
     db.commit()
    except sqlite3.IntegrityError:return self.fail('An account with this email already exists.',409)
   token=secrets.token_urlsafe(32);CLIENT_SESSIONS[token]=cur.lastrowid
   return self.reply({'ok':True,'client':{'name':name,'email':email}},201,{'Set-Cookie':client_cookie(token)})
  if path=='/api/client/login':
   email=clean(b.get('email'),200).lower();password=str(b.get('password',''))
   with conn() as db:r=db.execute('SELECT * FROM clients WHERE email=?',(email,)).fetchone()
   if not r or not hmac.compare_digest(password_hash(password,r['salt']),r['password_hash']):return self.fail('Incorrect email or password.',401)
   token=secrets.token_urlsafe(32);CLIENT_SESSIONS[token]=r['id']
   return self.reply({'ok':True,'client':{'name':r['name'],'email':r['email']}},extras={'Set-Cookie':client_cookie(token)})
  if path=='/api/client/logout':
   c=cookies.SimpleCookie()
   try:c.load(self.headers.get('Cookie',''))
   except cookies.CookieError:pass
   if 'lingap_client' in c:CLIENT_SESSIONS.pop(c['lingap_client'].value,None)
   return self.reply({'ok':True},extras={'Set-Cookie':client_cookie('',0)})
  if path=='/api/admin/login':
   user=clean(b.get('username'));pw=str(b.get('password',''))
   if not (hmac.compare_digest(user,ADMIN_USER) and hmac.compare_digest(pw,ADMIN_PASS)):
    return self.fail('Incorrect credentials.',401)
   token=secrets.token_urlsafe(32);SESSIONS[token]=True
   return self.reply({'ok':True},extras={'Set-Cookie':f'lingap_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800'})
  if path=='/api/admin/logout':
   c=cookies.SimpleCookie();c.load(self.headers.get('Cookie',''))
   if 'lingap_session' in c: SESSIONS.pop(c['lingap_session'].value,None)
   return self.reply({'ok':True},extras={'Set-Cookie':'lingap_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'})
  if path=='/api/intakes':
   cid=client_id(self)
   if b.get('consent') is not True: return self.fail('Consent is required.')
   name=clean(b.get('name'),120);email=clean(b.get('email'),200).lower()
   if len(name)<2 or not is_email(email):return self.fail('Name and valid email are required.')
   if cid:
    with conn() as db: registered_email=db.execute('SELECT email FROM clients WHERE id=?',(cid,)).fetchone()['email']
    if email!=registered_email:return self.fail('Use your account email for a linked application.')
   income=b.get('monthly_income');size=b.get('household_size')
   try: income=float(income) if income not in (None,'') else None;size=int(size) if size not in (None,'') else None
   except (ValueError,TypeError):return self.fail('Check your household information.')
   if income is not None and (income<0 or income>1e10):return self.fail('Invalid income.')
   if size is not None and not 1<=size<=100:return self.fail('Invalid household size.')
   category=clean(b.get('category'),80);assistance=clean(b.get('assistance'),60)
   if not category or not assistance:return self.fail('Complete the screening questions.')
   screening='For OLA review — no automatic eligibility determination'
   with LOCK:
    with conn() as db:
     stamp=now(); ref='OLA-'+datetime.now().strftime('%Y')+'-'+secrets.token_hex(3).upper()
     cur=db.execute('''INSERT INTO matters(reference,name,email,phone,city,language,assistance,household_size,monthly_income,category,summary,screening,consent_at,created_at,updated_at)
      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
      (ref,name,email,clean(b.get('phone'),30),clean(b.get('city'),100),clean(b.get('language'),2),assistance,size,income,category,clean(b.get('summary'),500),screening,stamp,stamp,stamp))
     if cid: db.execute('UPDATE matters SET client_id=? WHERE id=?',(cid,cur.lastrowid))
     db.execute('INSERT INTO events(matter_id,label,created_at) VALUES(?,?,?)',(cur.lastrowid,'Application received',stamp))
     send_notice(db,email,'applicant','Application received — '+ref,'Your LINGAP intake has been received. This is a demonstration notification; no email was sent.')
     db.commit()
   return self.reply({'reference':ref,'screening':screening,'message':'Your application was received for staff review.'},201)
  if path=='/api/appointments':
   ref=clean(b.get('reference'),30).upper();email=clean(b.get('email'),200).lower()
   day=clean(b.get('date'),10);time=clean(b.get('time'),5);typ=clean(b.get('type'),60)
   try: dt=date.fromisoformat(day)
   except ValueError:return self.fail('Invalid date.')
   if dt<date.today() or dt>date.today()+timedelta(days=60) or dt.weekday()>=5 or time not in ['09:00','10:00','11:00','13:00','14:00','15:00']:
    return self.fail('Choose an available weekday within the next 60 days.')
   with LOCK:
    with conn() as db:
     m=db.execute('SELECT id FROM matters WHERE reference=? AND lower(email)=?',(ref,email)).fetchone()
     if not m:return self.fail('Application reference and email do not match.',404)
     if db.execute('SELECT id FROM appointments WHERE matter_id=?',(m['id'],)).fetchone():return self.fail('This application already has an appointment.')
     try:db.execute('INSERT INTO appointments(matter_id,date,time,type,created_at) VALUES(?,?,?,?,?)',(m['id'],day,time,typ,now()))
     except sqlite3.IntegrityError:return self.fail('This slot was just taken. Select another.',409)
     db.execute('UPDATE matters SET status=?,updated_at=? WHERE id=?',('For appointment',now(),m['id']))
     db.execute('INSERT INTO events(matter_id,label,created_at) VALUES(?,?,?)',(m['id'],f'Appointment requested: {day} {time}',now()))
     send_notice(db,email,'appointment','Appointment request — '+ref,f'Appointment request for {day} at {time}. Subject to office confirmation. Demo only; not sent.')
     db.commit()
   return self.reply({'ok':True,'message':'Appointment request recorded; office confirmation is still required.'},201)
  if path=='/api/documents':
   ref=clean(b.get('reference'),30).upper();email=clean(b.get('email'),200).lower();filename=clean(b.get('filename'),180)
   if not re.search(r'\.(pdf|png|jpg|jpeg)$',filename,re.I):return self.fail('Allowed files: PDF, PNG, JPG.')
   try:raw=base64.b64decode(str(b.get('content','')),validate=True)
   except Exception:return self.fail('Invalid file.')
   if not raw or len(raw)>3_000_000:return self.fail('File must be 1 byte to 3 MB.')
   if not (raw.startswith(b'%PDF-') or raw.startswith(b'\x89PNG\r\n\x1a\n') or raw.startswith(b'\xff\xd8\xff')):return self.fail('File content does not match a supported format.')
   with conn() as db:
    m=db.execute('SELECT id FROM matters WHERE reference=? AND lower(email)=?',(ref,email)).fetchone()
    if not m:return self.fail('Application reference and email do not match.',404)
    stored=secrets.token_hex(20)+Path(filename).suffix.lower();(UPLOADS/stored).write_bytes(raw)
    db.execute('INSERT INTO documents(matter_id,filename,stored_name,size,created_at) VALUES(?,?,?,?,?)',(m['id'],filename,stored,len(raw),now()))
    db.execute('INSERT INTO events(matter_id,label,created_at) VALUES(?,?,?)',(m['id'],'Supporting document uploaded',now()))
    db.commit()
   return self.reply({'ok':True,'message':'Demo file stored locally. Do not use real client files.'},201)
  if path.startswith('/api/admin/'):
   if not self.require_admin():return
   m=re.fullmatch(r'/api/admin/matters/(\d+)/(status|assign)',path)
   if not m:return self.fail('Not found.',404)
   mid=int(m.group(1));act=m.group(2)
   with conn() as db:
    matter=db.execute('SELECT email,reference FROM matters WHERE id=?',(mid,)).fetchone()
    if not matter:return self.fail('Matter not found.',404)
    if act=='status':
     status=clean(b.get('status'),40)
     if status not in ALLOWED_STATUSES:return self.fail('Invalid status.')
     db.execute('UPDATE matters SET status=?,updated_at=? WHERE id=?',(status,now(),mid))
     label='Status changed to '+status
     send_notice(db,matter['email'],'status',f'Application update — {matter["reference"]}',label+' (demo only; not sent).')
    else:
     lawyer=clean(b.get('assigned_to'),100)
     if lawyer and lawyer not in [x[0] for x in LAWYERS]:return self.fail('Unknown lawyer.')
     db.execute('UPDATE matters SET assigned_to=?,updated_at=? WHERE id=?',(lawyer,now(),mid))
     label='Assigned to '+(lawyer or 'unassigned queue')
    db.execute('INSERT INTO events(matter_id,label,created_at) VALUES(?,?,?)',(mid,label,now()))
    db.commit()
   return self.reply({'ok':True})
  self.fail('Not found.',404)

if __name__=='__main__':
 init_db()
 print(f'LINGAP local prototype: http://{HOST}:{PORT}')
 print('DEMO ONLY: no real client data; no production safeguards or email delivery.')
 ThreadingHTTPServer((HOST,PORT),App).serve_forever()
