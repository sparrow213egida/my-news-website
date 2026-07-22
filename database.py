import sqlite3


def init_db():
    with sqlite3.connect("comments.db") as connection:
        cursor = connection.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_id INTEGER,
            author_name TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""")


def add_comment(author_name: str, content: str, parent_id: int | None) -> str:
    max_name_length = 50
    max_content_length = 1000

    if author_name == "":
        return "Имя автора комментария не может быть пустым"
    if len(author_name) > max_name_length:
        return "Длина имени автора комментария не может превышать 50 символов"
    if content == "":
        return "Комментарий не может быть пустым"
    if len(content) > max_content_length:
        return "Длина комментария не может превышать 1000 символов"

    with sqlite3.connect("comments.db") as connection:
        try:
            cursor = connection.cursor()
            cursor.execute("""INSERT INTO comments (parent_id, author_name, content)
            VALUES (?, ?, ?)""", (parent_id, author_name, content))
            return ""
        except Exception as err:
            return f"An error occurred: {err}"


def get_all_comments() -> list[dict]:
    list_of_comments = []

    with sqlite3.connect("comments.db") as connection:
        cursor = connection.cursor()
        comments = cursor.execute("SELECT * FROM comments ORDER BY created_at").fetchall()
        for comment in comments:
            list_of_comments.append({"id": comment[0], "parent_id": comment[1], "author_name": comment[2],
                                     "content": comment[3], "created_at": comment[4]})

    return list_of_comments
