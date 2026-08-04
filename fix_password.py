import sqlite3
db = sqlite3.connect('/home/gfnj95/gfnj-inventory/data.db')
db.execute("UPDATE users SET password='gfnj@2026' WHERE username='owner'")
db.execute("UPDATE users SET password='123456' WHERE username='clerk'")
db.commit()
cur = db.execute('SELECT username, password FROM users')
for r in cur.fetchall():
    print(r)
db.close()
