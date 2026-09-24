import json, sqlite3, uuid, time, os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=Path(os.environ.get('AUDIO_LAB_DATA',str(ROOT/'data')))
DATA.mkdir(parents=True,exist_ok=True)

def connection():
 c=sqlite3.connect(DATA/'lab.sqlite',timeout=30);c.row_factory=sqlite3.Row
 return c

def init():
 with connection() as c:
  c.execute('PRAGMA journal_mode=WAL')
  for table in ('assets','cases','jobs','candidates'):
   c.execute(f'CREATE TABLE IF NOT EXISTS {table} (id TEXT PRIMARY KEY, created REAL NOT NULL, payload TEXT NOT NULL)')
 for j in all_rows('jobs'):
  if j['status'] in ('queued','running'):
   update('jobs',j['id'],status='interrupted',stage='上次處理中斷',error='服務已重新啟動，請重新提交。')

def put(table,values):
 values={'id':uuid.uuid4().hex,'created':time.time(),**values}
 with connection() as c:c.execute(f'INSERT INTO {table} VALUES (?,?,?)',(values['id'],values['created'],json.dumps(values,ensure_ascii=False)))
 return values

def get(table,id):
 with connection() as c:r=c.execute(f'SELECT payload FROM {table} WHERE id=?',(id,)).fetchone()
 if not r:raise KeyError(id)
 return json.loads(r[0])

def all_rows(table):
 with connection() as c:r=c.execute(f'SELECT payload FROM {table} ORDER BY created DESC').fetchall()
 return [json.loads(x[0]) for x in r]

def update(table,id,**changes):
 with connection() as c:
  c.execute('BEGIN IMMEDIATE')
  row=c.execute(f'SELECT payload FROM {table} WHERE id=?',(id,)).fetchone()
  if not row:raise KeyError(id)
  value={**json.loads(row[0]),**changes}
  c.execute(f'UPDATE {table} SET payload=? WHERE id=?',(json.dumps(value,ensure_ascii=False),id))
 return value
