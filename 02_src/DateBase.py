import sqlite3

conn = sqlite3.connect('database.db')
c = conn.cursor()

# 外部キー制約を有効化
c.execute('PRAGMA foreign_keys = ON;')

# usersテーブル
# c.execute('''
# CREATE TABLE IF NOT EXISTS users (
#     user_id INTEGER PRIMARY KEY AUTOINCREMENT,
#     user_name VARCHAR(32) NOT NULL,
#     role VARCHAR(32) NOT NULL,
#     register_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#     password_hash VARCHAR(64)
# )
# ''')

# cardテーブル
c.execute('''
CREATE TABLE IF NOT EXISTS card (
    card_id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_name TEXT NOT NULL,
    card_number TEXT NOT NULL,
    register_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    
)
''')

# access_logsテーブル
c.execute('''
CREATE TABLE IF NOT EXISTS access_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    method VARCHAR(32) NOT NULL,
    card_id INTEGER,
    foreign key(card_id) references card(card_id)
)
''')

# usersテーブルにサンプルデータを挿入(hashされたパスワードは'trytokyo'のSHA-256ハッシュ)
# c.execute('''
# INSERT INTO users (user_name, role, password_hash) VALUES ('admin', 'administrator', '00e9291bcbef0095a7e849c2ea3c9d6ca68c11f94be79e271dc19f33bedabdeb')
# ''')
# cardテーブルにサンプルデータを挿入
c.execute('''
INSERT INTO card (card_name, card_number) VALUES ('Sample Card', '1234567890123456')
''')  
          
# access_logsテーブルにサンプルデータを挿入
c.execute('''
INSERT INTO access_logs (card_id, method) VALUES (1, 'Web')
''')

conn.commit()
conn.close()