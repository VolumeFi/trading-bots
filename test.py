import sqlite3
con = sqlite3.connect('momentum_cache.db')
cur = con.cursor()
for row in cur.execute('SELECT * FROM cache ;'):
    print(row)

