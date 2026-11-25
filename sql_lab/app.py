import random
import sqlite3
from flask import Flask, render_template, request

app = Flask(__name__)
DB_PATH = "lab.db"

FIRST_NAMES = ["Minh", "An", "Khoa", "Linh", "Nam", "Trang", "Huy", "Vy", "Duc", "Ngoc"]
LAST_NAMES = ["Nguyen", "Tran", "Le", "Pham", "Hoang", "Vo", "Dang", "Bui"]
COURSE_TITLES = [
    "SQL Fundamentals",
    "Database Design",
    "Web Security Basics",
    "Linux & Networking",
    "Data Structures",
    "Python Programming",
]


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    conn = get_db_connection()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            age INTEGER CHECK (age >= 16 AND age <= 100),
            gpa REAL DEFAULT 0.0
        );

        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            course_name TEXT NOT NULL,
            credits INTEGER DEFAULT 3,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
        );
        """
    )
    conn.commit()
    conn.close()


def seed_random_data(num_students=5, num_courses=6):
    conn = get_db_connection()
    suffix = random.randint(1000, 999999)

    created_student_ids = []
    for i in range(num_students):
        full_name = f"{random.choice(LAST_NAMES)} {random.choice(FIRST_NAMES)}"
        email = f"sv_{suffix}_{i}@example.edu.vn"
        age = random.randint(18, 24)
        gpa = round(random.uniform(2.0, 4.0), 2)
        cur = conn.execute(
            "INSERT INTO students (full_name, email, age, gpa) VALUES (?, ?, ?, ?);",
            (full_name, email, age, gpa),
        )
        created_student_ids.append(cur.lastrowid)

    all_student_rows = conn.execute("SELECT id FROM students;").fetchall()
    all_student_ids = [r["id"] for r in all_student_rows] or created_student_ids

    if all_student_ids:
        for _ in range(num_courses):
            sid = random.choice(all_student_ids)
            cname = random.choice(COURSE_TITLES)
            credits = random.choice([2, 3, 4])
            conn.execute(
                "INSERT INTO courses (student_id, course_name, credits) VALUES (?, ?, ?);",
                (sid, cname, credits),
            )

    conn.commit()
    conn.close()


def get_tables_with_preview(conn):
    table_rows = conn.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
    ).fetchall()

    result = []
    for t in table_rows:
        t_name = t["name"]
        # Tên bảng đã lấy từ sqlite_master nội bộ, an toàn để hiển thị preview tối đa 10 dòng
        rows = conn.execute(f'SELECT * FROM "{t_name}" LIMIT 10;').fetchall()
        columns = rows[0].keys() if rows else []
        result.append(
            {
                "name": t_name,
                "sql": t["sql"],
                "columns": columns,
                "rows": [dict(r) for r in rows],
            }
        )
    return result


@app.route("/", methods=["GET", "POST"])
def index():
    init_db()
    message = None
    error = None
    sql_query = ""
    select_columns = []
    select_rows = []

    conn = get_db_connection()

    if request.method == "POST":
        action = request.form.get("action", "run_sql")

        if action == "seed_random":
            try:
                seed_random_data(num_students=5, num_courses=6)
                message = "Đã thêm ngẫu nhiên 5 sinh viên và 6 lượt đăng ký môn học!"
            except sqlite3.Error as e:
                error = f"Lỗi khi sinh dữ liệu ngẫu nhiên: {e}"

        elif action == "reset_db":
            conn.close()
            import os
            if os.path.exists(DB_PATH):
                os.remove(DB_PATH)
            init_db()
            seed_random_data(num_students=5, num_courses=6)
            conn = get_db_connection()
            message = "Đã reset lại lab.db và nạp dữ liệu ngẫu nhiên mới!"

        else:
            sql_query = request.form.get("sql_query", "").strip()
            if not sql_query:
                error = "Bạn chưa nhập câu lệnh SQL."
            else:
                try:
                    # Nếu là câu lệnh truy vấn đọc dữ liệu đơn lẻ thì trả về bảng kết quả
                    upper_sql = sql_query.lstrip().upper()
                    if (upper_sql.startswith("SELECT") or upper_sql.startswith("PRAGMA")) and sql_query.count(";") <= 1:
                        cur = conn.execute(sql_query)
                        fetched = cur.fetchall()
                        select_columns = [d[0] for d in cur.description] if cur.description else []
                        select_rows = [dict(zip(select_columns, r)) for r in fetched]
                        message = f"Truy vấn thành công ({len(select_rows)} dòng)."
                    else:
                        conn.executescript(sql_query)
                        conn.commit()
                        message = "Thực thi câu lệnh SQL thành công!"
                except sqlite3.Error as e:
                    error = f"Lỗi SQL, THẰNG THẤT BẠI : {e}"

    tables = get_tables_with_preview(conn)
    conn.close()

    return render_template(
        "index.html",
        sql_query=sql_query,
        message=message,
        error=error,
        tables=tables,
        select_columns=select_columns,
        select_rows=select_rows,
    )


if __name__ == "__main__":
    init_db()
    conn_check = get_db_connection()
    existing = conn_check.execute("SELECT COUNT(*) AS cnt FROM students;").fetchone()["cnt"]
    conn_check.close()
    if existing == 0:
        seed_random_data(num_students=5, num_courses=6)
    app.run(host="0.0.0.0", port=5000, debug=True)