import sys
sys.path.insert(0, ".")

import sqlite3
from app.core.security import hash_password, verify_password

conn = sqlite3.connect("kg_ai.db")
cur = conn.cursor()

# 先看看数据库里的 hash
row = cur.execute("SELECT id, email, hashed_password FROM users WHERE email=?", ("admin@kg.com",)).fetchone()
if row:
    print("数据库现有hash:", row[2][:30], "...")
    ok = verify_password("admin", row[2])
    print("admin 验证:", ok)
    
    # 删除重建
    cur.execute("DELETE FROM users WHERE email='admin@kg.com'")

# 用项目的 hash_password 重建
hashed = hash_password("admin")
cur.execute(
    "INSERT INTO users (email, hashed_password, display_name, is_active, role) VALUES (?, ?, ?, ?, ?)",
    ("admin@kg.com", hashed, "管理员", True, "admin"),
)
conn.commit()

# 验证
row2 = cur.execute("SELECT id, email, hashed_password FROM users WHERE email=?", ("admin@kg.com",)).fetchone()
ok2 = verify_password("admin", row2[2])
print(f"新建后验证 admin: {ok2}")
print(f"账户: admin@kg.com / admin")

conn.close()
