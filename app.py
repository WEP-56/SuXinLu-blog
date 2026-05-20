import os
import random
import re
import sqlite3
import uuid
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    Response,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or "suxinlu-dev-secret-change-me"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "blog.db"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_TAG = "生活随笔"
DEFAULT_ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "suchinlu2025")
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
QUOTES = [
    "无可奈何花落去，似曾相识燕归来。",
    "春风得意马蹄疾，一日看尽长安花。",
    "最是人间留不住，朱颜辞镜花辞树。",
    "读书之乐乐何如，绿满窗前草不除。",
    "竹杖芒鞋轻胜马，谁怕？一蓑烟雨任平生。",
    "山中何事？松花酿酒，春水煎茶。",
    "行到水穷处，坐看云起时。",
    "小楼一夜听春雨，深巷明朝卖杏花。",
    "被酒莫惊春睡重，赌书消得泼茶香。",
    "且将新火试新茶，诗酒趁年华。",
    "晚来天欲雪，能饮一杯无？",
    "云想衣裳花想容，春风拂槛露华浓。",
    "疏影横斜水清浅，暗香浮动月黄昏。",
    "人闲桂花落，夜静春山空。",
    "一川烟草，满城风絮，梅子黄时雨。",
    "荷风送香气，竹露滴清响。",
    "明月松间照，清泉石上流。",
    "细雨湿衣看不见，闲花落地听无声。",
]


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.execute("PRAGMA journal_mode = WAL")
    return g.db


@app.teardown_appcontext
def close_db(_exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def table_columns(db, table_name: str) -> set[str]:
    rows = db.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def ensure_post_columns(db):
    columns = table_columns(db, "posts")
    if "status" not in columns:
        db.execute(
            "ALTER TABLE posts ADD COLUMN status TEXT NOT NULL DEFAULT 'published'"
        )
    if "updated_at" not in columns:
        db.execute("ALTER TABLE posts ADD COLUMN updated_at TEXT")
    if "published_at" not in columns:
        db.execute("ALTER TABLE posts ADD COLUMN published_at TEXT")

    db.execute(
        "UPDATE posts SET updated_at = COALESCE(updated_at, created_at, ?) "
        "WHERE updated_at IS NULL OR updated_at = ''",
        [now_str()],
    )
    db.execute(
        "UPDATE posts SET published_at = COALESCE(published_at, created_at, updated_at) "
        "WHERE status = 'published' AND (published_at IS NULL OR published_at = '')"
    )


def init_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            tag TEXT DEFAULT '生活随笔',
            status TEXT NOT NULL DEFAULT 'published',
            views INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0,
            image TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            published_at TEXT
        );

        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            author_name TEXT NOT NULL,
            content TEXT NOT NULL,
            approved INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        );
        """
    )
    ensure_post_columns(db)

    admin = db.execute("SELECT id FROM admin LIMIT 1").fetchone()
    if not admin:
        db.execute(
            "INSERT INTO admin (username, password_hash) VALUES (?, ?)",
            [DEFAULT_ADMIN_USERNAME, generate_password_hash(DEFAULT_ADMIN_PASSWORD)],
        )

    db.commit()
    db.close()


def remove_uploaded_image(image_path: str | None):
    if not image_path:
        return
    full_path = BASE_DIR / image_path.lstrip("/").replace("/", os.sep)
    if full_path.exists() and full_path.is_file():
        full_path.unlink()


def save_uploaded_image(file_storage, current_path: str = "") -> str:
    if not file_storage or not file_storage.filename:
        return current_path

    ext = Path(file_storage.filename).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError("仅支持 jpg、jpeg、png、gif、webp 图片。")

    filename = f"{uuid.uuid4().hex}{ext}"
    target = UPLOAD_DIR / filename
    file_storage.save(target)

    if current_path:
        remove_uploaded_image(current_path)

    return f"/static/uploads/{filename}"


def fetch_post(post_id: int, include_drafts: bool = False):
    db = get_db()
    if include_drafts:
        return db.execute("SELECT * FROM posts WHERE id = ?", [post_id]).fetchone()
    return db.execute(
        "SELECT * FROM posts WHERE id = ? AND status = 'published'",
        [post_id],
    ).fetchone()


def post_sort_field() -> str:
    return "COALESCE(published_at, created_at)"


def month_to_chinese(month_str: str) -> str:
    seasons = {
        "01": "冬",
        "02": "冬",
        "03": "春",
        "04": "春",
        "05": "春",
        "06": "夏",
        "07": "夏",
        "08": "夏",
        "09": "秋",
        "10": "秋",
        "11": "秋",
        "12": "冬",
    }
    digits = "零一二三四五六七八九"
    try:
        year, month = month_str.split("-")
        year_cn = "".join(digits[int(char)] for char in year)
        return f"{year_cn}年 · {seasons.get(month, month)}"
    except (ValueError, IndexError):
        return month_str


@app.template_filter("excerpt")
def excerpt(text: str | None, length: int = 120):
    text = (text or "").strip().replace("\n", " ")
    return f"{text[:length]}…" if len(text) > length else text


@app.template_filter("format_content")
def format_content(text: str | None):
    if not text:
        return ""
    paragraphs = re.split(r"\n\s*\n", text.strip())
    return "\n".join(
        f"<p>{paragraph.strip().replace(chr(10), '<br>')}</p>"
        for paragraph in paragraphs
        if paragraph.strip()
    )


@app.template_filter("cn_date")
def cn_date(date_str: str | None):
    if not date_str:
        return ""
    for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(str(date_str), pattern)
            return dt.strftime("%Y年%m月%d日")
        except ValueError:
            continue
    return str(date_str)


@app.template_filter("cn_month")
def cn_month(month_str: str | None):
    if not month_str:
        return ""
    return month_to_chinese(str(month_str))


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login", next=request.path))
        return func(*args, **kwargs)

    return wrapper


@app.before_request
def ensure_database():
    if not getattr(app, "_db_ready", False):
        init_db()
        app._db_ready = True


@app.route("/")
def index():
    month = (request.args.get("month") or "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}", month):
        month = ""

    db = get_db()
    params = []
    where = "WHERE status = 'published'"
    if month:
        where += " AND substr(COALESCE(published_at, created_at), 1, 7) = ?"
        params.append(month)

    posts = db.execute(
        f"""
        SELECT id, title, content, tag, views, likes, image, created_at, published_at
        FROM posts
        {where}
        ORDER BY {post_sort_field()} DESC, id DESC
        """,
        params,
    ).fetchall()
    archives = db.execute(
        f"""
        SELECT substr({post_sort_field()}, 1, 7) AS month_key, COUNT(*) AS total
        FROM posts
        WHERE status = 'published'
        GROUP BY month_key
        ORDER BY month_key DESC
        """
    ).fetchall()
    return render_template(
        "index.html",
        posts=posts,
        archives=archives,
        quote=random.choice(QUOTES),
        current_month=month,
        current_month_label=month_to_chinese(month) if month else "",
    )


@app.route("/about")
def about():
    links = [
        {"name": "小红书", "url": "https://www.xiaohongshu.com/"},
        {"name": "微信公众号", "url": "https://mp.weixin.qq.com/"},
        {"name": "微博", "url": "https://weibo.com/"},
        {"name": "哔哩哔哩", "url": "https://www.bilibili.com/"},
    ]
    return render_template("about.html", links=links, quote=random.choice(QUOTES))


@app.route("/post/<int:post_id>")
def post_detail(post_id: int):
    db = get_db()
    post = fetch_post(post_id)
    if not post:
        flash("未找到这篇文章。")
        return redirect(url_for("index"))

    db.execute("UPDATE posts SET views = views + 1 WHERE id = ?", [post_id])
    db.commit()
    post = fetch_post(post_id)

    comments = db.execute(
        """
        SELECT id, author_name, content, created_at
        FROM comments
        WHERE post_id = ? AND approved = 1
        ORDER BY created_at DESC, id DESC
        """,
        [post_id],
    ).fetchall()
    prev_post = db.execute(
        """
        SELECT id, title
        FROM posts
        WHERE status = 'published' AND id < ?
        ORDER BY id DESC
        LIMIT 1
        """,
        [post_id],
    ).fetchone()
    next_post = db.execute(
        """
        SELECT id, title
        FROM posts
        WHERE status = 'published' AND id > ?
        ORDER BY id ASC
        LIMIT 1
        """,
        [post_id],
    ).fetchone()
    return render_template(
        "post.html",
        post=post,
        comments=comments,
        prev_post=prev_post,
        next_post=next_post,
    )


@app.route("/post/<int:post_id>/comment", methods=["POST"])
def add_comment(post_id: int):
    if not fetch_post(post_id):
        return jsonify({"ok": False, "msg": "文章不存在。"})

    author = (request.form.get("author") or "").strip()
    content = (request.form.get("content") or "").strip()
    if not author or not content:
        return jsonify({"ok": False, "msg": "昵称和留言内容都要填写。"})
    if len(author) > 20 or len(content) > 2000:
        return jsonify({"ok": False, "msg": "字数超出限制。"})

    db = get_db()
    db.execute(
        "INSERT INTO comments (post_id, author_name, content, approved, created_at) "
        "VALUES (?, ?, ?, 0, ?)",
        [post_id, author, content, now_str()],
    )
    db.commit()
    return jsonify({"ok": True, "msg": "留言已收到，待后台审核后显示。"})


@app.route("/post/<int:post_id>/like", methods=["POST"])
def like_post(post_id: int):
    if not fetch_post(post_id):
        return jsonify({"ok": False, "msg": "文章不存在。"})

    cookie_name = f"liked_{post_id}"
    if request.cookies.get(cookie_name):
        return jsonify({"ok": False, "msg": "这篇文章你已经点过赞了。"})

    db = get_db()
    db.execute("UPDATE posts SET likes = likes + 1 WHERE id = ?", [post_id])
    db.commit()
    likes = db.execute("SELECT likes FROM posts WHERE id = ?", [post_id]).fetchone()
    response = jsonify({"ok": True, "likes": likes["likes"]})
    response.set_cookie(cookie_name, "1", max_age=60 * 60 * 24 * 365)
    return response


@app.route("/favicon.ico")
def favicon():
    return Response(status=204)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()
        remember_login = request.form.get("remember_login") == "1"
        admin = get_db().execute(
            "SELECT * FROM admin WHERE username = ?",
            [username],
        ).fetchone()
        if admin and check_password_hash(admin["password_hash"], password):
            session["logged_in"] = True
            session["admin_name"] = admin["username"]
            session.permanent = remember_login
            target = (request.args.get("next") or "").strip()
            return redirect(target or url_for("admin_dashboard"))
        error = "账号或密码不对，请再试一次。"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    flash("已退出后台。")
    return redirect(url_for("index"))


@app.route("/admin")
@login_required
def admin_dashboard():
    db = get_db()
    stats = {
        "published_count": db.execute(
            "SELECT COUNT(*) AS total FROM posts WHERE status = 'published'"
        ).fetchone()["total"],
        "draft_count": db.execute(
            "SELECT COUNT(*) AS total FROM posts WHERE status = 'draft'"
        ).fetchone()["total"],
        "comment_count": db.execute(
            "SELECT COUNT(*) AS total FROM comments WHERE approved = 1"
        ).fetchone()["total"],
        "pending_count": db.execute(
            "SELECT COUNT(*) AS total FROM comments WHERE approved = 0"
        ).fetchone()["total"],
        "total_likes": db.execute(
            "SELECT COALESCE(SUM(likes), 0) AS total FROM posts WHERE status = 'published'"
        ).fetchone()["total"],
    }
    pending_comments = db.execute(
        """
        SELECT comments.id, comments.content, comments.author_name, comments.created_at,
               comments.post_id, posts.title AS post_title
        FROM comments
        JOIN posts ON posts.id = comments.post_id
        WHERE comments.approved = 0
        ORDER BY comments.created_at DESC, comments.id DESC
        """
    ).fetchall()
    drafts = db.execute(
        """
        SELECT id, title, tag, updated_at, created_at
        FROM posts
        WHERE status = 'draft'
        ORDER BY updated_at DESC, id DESC
        """
    ).fetchall()
    posts = db.execute(
        """
        SELECT id, title, tag, views, likes, published_at
        FROM posts
        WHERE status = 'published'
        ORDER BY COALESCE(published_at, created_at) DESC, id DESC
        """
    ).fetchall()
    return render_template(
        "admin.html",
        stats=stats,
        drafts=drafts,
        posts=posts,
        pending_comments=pending_comments,
        admin_name=session.get("admin_name", DEFAULT_ADMIN_USERNAME),
    )


@app.route("/admin/jump")
@login_required
def admin_jump():
    post_id = request.args.get("post_id", type=int)
    if not post_id:
        flash("请输入正确的编号。")
        return redirect(url_for("admin_dashboard"))

    post = fetch_post(post_id, include_drafts=True)
    if not post:
        flash(f"没有找到编号 #{post_id}。")
        return redirect(url_for("admin_dashboard"))

    if post["status"] == "draft":
        return redirect(url_for("creator", post_id=post_id))
    return redirect(url_for("post_detail", post_id=post_id))


@app.route("/admin/write")
@login_required
def creator():
    post_id = request.args.get("post_id", type=int)
    current_draft = None
    if post_id:
        draft = fetch_post(post_id, include_drafts=True)
        if draft and draft["status"] == "draft":
            current_draft = draft
        else:
            flash("只能继续编辑草稿，已发布文章请先重新起草。")
            return redirect(url_for("admin_dashboard"))

    db = get_db()
    drafts = db.execute(
        """
        SELECT id, title, tag, updated_at
        FROM posts
        WHERE status = 'draft'
        ORDER BY updated_at DESC, id DESC
        """
    ).fetchall()
    published_posts = db.execute(
        """
        SELECT id, title, tag, published_at
        FROM posts
        WHERE status = 'published'
        ORDER BY COALESCE(published_at, created_at) DESC, id DESC
        LIMIT 8
        """
    ).fetchall()
    return render_template(
        "creator.html",
        draft=current_draft,
        drafts=drafts,
        published_posts=published_posts,
        default_tag=DEFAULT_TAG,
    )


def save_post_from_form(action: str):
    post_id = request.form.get("post_id", type=int)
    title = (request.form.get("title") or "").strip()
    content = (request.form.get("content") or "").strip()
    tag = (request.form.get("tag") or DEFAULT_TAG).strip() or DEFAULT_TAG
    remove_image = request.form.get("remove_image") == "1"

    draft = None
    current_image = ""
    if post_id:
        draft = fetch_post(post_id, include_drafts=True)
        if not draft or draft["status"] != "draft":
            flash("只能保存或发布草稿。")
            return redirect(url_for("admin_dashboard"))
        current_image = draft["image"] or ""

    if action == "publish":
        if not title or not content:
            flash("发布前至少要把标题和正文写好。")
            return redirect(url_for("creator", post_id=post_id) if post_id else url_for("creator"))
    elif not title and not content:
        flash("标题和正文至少写一项，再保存草稿。")
        return redirect(url_for("creator", post_id=post_id) if post_id else url_for("creator"))

    if remove_image and current_image:
        remove_uploaded_image(current_image)
        current_image = ""

    try:
        image_path = save_uploaded_image(request.files.get("image"), current_image)
    except ValueError as exc:
        flash(str(exc))
        return redirect(url_for("creator", post_id=post_id) if post_id else url_for("creator"))

    db = get_db()
    timestamp = now_str()
    status = "published" if action == "publish" else "draft"

    if draft:
        published_at = draft["published_at"]
        if status == "published" and not published_at:
            published_at = timestamp
        db.execute(
            """
            UPDATE posts
            SET title = ?, content = ?, tag = ?, image = ?, status = ?,
                updated_at = ?, published_at = ?
            WHERE id = ?
            """,
            [
                title or "未命名草稿",
                content,
                tag,
                image_path,
                status,
                timestamp,
                published_at,
                post_id,
            ],
        )
        target_id = post_id
    else:
        published_at = timestamp if status == "published" else None
        cursor = db.execute(
            """
            INSERT INTO posts (
                title, content, tag, status, image, created_at, updated_at, published_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                title or "未命名草稿",
                content,
                tag,
                status,
                image_path,
                timestamp,
                timestamp,
                published_at,
            ],
        )
        target_id = cursor.lastrowid

    db.commit()

    if status == "draft":
        flash(f"草稿 #{target_id} 已保存。")
        return redirect(url_for("creator", post_id=target_id))

    flash(f"文章 #{target_id} 已发布。")
    return redirect(url_for("post_detail", post_id=target_id))


@app.route("/admin/editor/submit", methods=["POST"])
@login_required
def editor_submit():
    action = (request.form.get("action") or "").strip()
    if action not in {"draft", "publish"}:
        flash("未识别的操作。")
        return redirect(url_for("creator"))
    return save_post_from_form(action)


@app.route("/admin/draft/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_draft(post_id: int):
    db = get_db()
    draft = fetch_post(post_id, include_drafts=True)
    if draft and draft["status"] == "draft":
        remove_uploaded_image(draft["image"])
        db.execute("DELETE FROM posts WHERE id = ?", [post_id])
        db.commit()
        flash(f"草稿 #{post_id} 已删除。")
    else:
        flash("草稿不存在。")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/post/<int:post_id>/fork", methods=["POST"])
@login_required
def fork_post(post_id: int):
    db = get_db()
    post = fetch_post(post_id)
    if not post:
        flash("要重新起草的文章不存在。")
        return redirect(url_for("admin_dashboard"))

    timestamp = now_str()
    cursor = db.execute(
        """
        INSERT INTO posts (
            title, content, tag, status, image, views, likes, created_at, updated_at, published_at
        ) VALUES (?, ?, ?, 'draft', ?, 0, 0, ?, ?, NULL)
        """,
        [
            f"{post['title']}（修订稿）",
            post["content"],
            post["tag"],
            post["image"],
            timestamp,
            timestamp,
        ],
    )
    db.commit()
    flash(f"已生成修订草稿 #{cursor.lastrowid}。")
    return redirect(url_for("creator", post_id=cursor.lastrowid))


@app.route("/admin/post/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id: int):
    db = get_db()
    post = fetch_post(post_id, include_drafts=True)
    if not post:
        flash("文章不存在。")
        return redirect(url_for("admin_dashboard"))

    remove_uploaded_image(post["image"])
    db.execute("DELETE FROM posts WHERE id = ?", [post_id])
    db.commit()
    flash(f"文章 #{post_id} 已删除。")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/comment/<int:comment_id>/approve", methods=["POST"])
@login_required
def approve_comment(comment_id: int):
    db = get_db()
    db.execute("UPDATE comments SET approved = 1 WHERE id = ?", [comment_id])
    db.commit()
    return jsonify({"ok": True})


@app.route("/admin/comment/<int:comment_id>/reject", methods=["POST"])
@login_required
def reject_comment(comment_id: int):
    db = get_db()
    db.execute("DELETE FROM comments WHERE id = ?", [comment_id])
    db.commit()
    return jsonify({"ok": True})


@app.route("/admin/change-password", methods=["POST"])
@login_required
def change_password():
    new_password = (request.form.get("new_password") or "").strip()
    if len(new_password) < 4:
        flash("新密码至少 4 位。")
        return redirect(url_for("admin_dashboard"))

    db = get_db()
    db.execute(
        "UPDATE admin SET password_hash = ? WHERE username = ?",
        [generate_password_hash(new_password), session.get("admin_name")],
    )
    db.commit()
    flash("密码已更新。")
    return redirect(url_for("admin_dashboard"))


if __name__ == "__main__":
    init_db()
    app.run(debug=False, host="0.0.0.0", port=5000)
