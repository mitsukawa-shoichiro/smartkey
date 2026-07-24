CREATE TABLE access_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT (datetime('now', 'localtime')),
    method VARCHAR(32) NOT NULL,
    card_id INTEGER,
    eventtype INTEGER,
    FOREIGN KEY(card_id) REFERENCES card(card_id)
)
method
カード
card_id
---
顔認証
face_id
