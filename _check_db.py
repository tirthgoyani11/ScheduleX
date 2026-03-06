import sqlite3
c = sqlite3.connect('timetable_dev.db')
tables = c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("Tables:", [t[0] for t in tables])
for t in tables:
    name = t[0]
    cnt = c.execute(f"SELECT COUNT(*) FROM [{name}]").fetchone()[0]
    print(f"  {name}: {cnt} rows")
    if name == 'timetable':
        rows = c.execute("SELECT timetable_id, semester, status FROM timetable").fetchall()
        for r in rows:
            print(f"    {r}")
