import os, sqlite3, json, uuid
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("ROOMFINDER_SECRET", "replace-this-secret-before-deployment")
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024
ROOT = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(ROOT, "roomfinder.db")
UPLOADS = os.path.join(ROOT, "static", "uploads")
os.makedirs(UPLOADS, exist_ok=True)
ALLOWED = {"jpg", "jpeg", "png", "webp"}
app.jinja_env.filters["fromjson"] = json.loads

def connect():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with connect() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS owners(
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, mobile TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS properties(
            id INTEGER PRIMARY KEY, owner_id INTEGER NOT NULL, title TEXT NOT NULL,
            city TEXT NOT NULL, area TEXT NOT NULL, address TEXT NOT NULL,
            rent INTEGER NOT NULL, room_type TEXT NOT NULL, description TEXT,
            photos TEXT NOT NULL, status TEXT DEFAULT 'Pending',
            FOREIGN KEY(owner_id) REFERENCES owners(id))""")
        c.execute("""CREATE TABLE IF NOT EXISTS admins(
            id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL)""")
        if not c.execute("SELECT id FROM admins WHERE username='admin'").fetchone():
            c.execute("INSERT INTO admins(username,password_hash) VALUES(?,?)",
                      ("admin", generate_password_hash("ChangeMe123!")))

def owner_only(fn):
    @wraps(fn)
    def wrapped(*a, **kw):
        if "owner_id" not in session:
            flash("Please login as an owner first.", "warning")
            return redirect(url_for("owner_login"))
        return fn(*a, **kw)
    return wrapped

def admin_only(fn):
    @wraps(fn)
    def wrapped(*a, **kw):
        if "admin_id" not in session:
            return redirect(url_for("admin_login"))
        return fn(*a, **kw)
    return wrapped

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/search")
def search():
    city, area = request.args.get("city",""), request.args.get("area","")
    kind, maximum = request.args.get("room_type",""), request.args.get("max_rent","")
    sql = "SELECT * FROM properties WHERE status='Approved'"
    args = []
    for col, val in (("city",city),("area",area),("room_type",kind)):
        if val: sql += f" AND {col}=?"; args.append(val)
    if maximum.isdigit(): sql += " AND rent<=?"; args.append(int(maximum))
    sql += " ORDER BY rent"
    with connect() as c: rooms = c.execute(sql,args).fetchall()
    return render_template("search.html", rooms=rooms, city=city, area=area, kind=kind, maximum=maximum)

@app.route("/room/<int:rid>")
def room_detail(rid):
    with connect() as c:
        room = c.execute("""SELECT p.*,o.name owner_name,o.mobile owner_mobile
            FROM properties p JOIN owners o ON o.id=p.owner_id
            WHERE p.id=? AND p.status='Approved'""",(rid,)).fetchone()
    if not room: abort(404)
    return render_template("room_detail.html", room=room, photos=json.loads(room["photos"]))

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name=request.form.get("name","").strip()
        mobile=request.form.get("mobile","").strip()
        password=request.form.get("password","")
        if not name or not mobile or len(password)<6:
            flash("Enter name, mobile and password (minimum 6 characters).","danger")
        else:
            try:
                with connect() as c:
                    c.execute("INSERT INTO owners(name,mobile,password_hash) VALUES(?,?,?)",
                              (name,mobile,generate_password_hash(password)))
                flash("Account created. Please login.","success")
                return redirect(url_for("owner_login"))
            except sqlite3.IntegrityError:
                flash("Mobile number already registered.","danger")
    return render_template("register.html")

@app.route("/owner-login", methods=["GET","POST"])
def owner_login():
    if request.method=="POST":
        with connect() as c:
            owner=c.execute("SELECT * FROM owners WHERE mobile=?",(request.form.get("mobile","").strip(),)).fetchone()
        if owner and check_password_hash(owner["password_hash"],request.form.get("password","")):
            session.clear(); session["owner_id"]=owner["id"]; session["owner_name"]=owner["name"]
            return redirect(url_for("owner_dashboard"))
        flash("Incorrect mobile number or password.","danger")
    return render_template("owner_login.html")

@app.route("/owner")
@owner_only
def owner_dashboard():
    with connect() as c:
        rooms=c.execute("SELECT * FROM properties WHERE owner_id=? ORDER BY id DESC",(session["owner_id"],)).fetchall()
    return render_template("owner_dashboard.html",rooms=rooms)

@app.route("/add-property",methods=["GET","POST"])
@owner_only
def add_property():
    if request.method=="POST":
        data={k:request.form.get(k,"").strip() for k in
              ["title","city","area","address","rent","room_type","description"]}
        photos=[p for p in request.files.getlist("photos") if p and p.filename]
        valid=lambda f:"." in f and f.rsplit(".",1)[1].lower() in ALLOWED
        if not all(data[k] for k in ["title","city","area","address","rent","room_type"]):
            flash("Please fill all required fields.","danger")
        elif not data["rent"].isdigit() or int(data["rent"])<1:
            flash("Enter a valid rent.","danger")
        elif not photos or any(not valid(p.filename) for p in photos):
            flash("Upload at least one JPG, PNG or WEBP photo.","danger")
        else:
            names=[]
            for p in photos:
                ext=p.filename.rsplit(".",1)[1].lower()
                filename=secure_filename(uuid.uuid4().hex+"."+ext)
                p.save(os.path.join(UPLOADS,filename)); names.append(filename)
            with connect() as c:
                c.execute("""INSERT INTO properties(owner_id,title,city,area,address,rent,room_type,description,photos)
                    VALUES(?,?,?,?,?,?,?,?,?)""",
                    (session["owner_id"],data["title"],data["city"],data["area"],data["address"],
                     int(data["rent"]),data["room_type"],data["description"],json.dumps(names)))
            flash("Property submitted. It will appear after admin approval.","success")
            return redirect(url_for("owner_dashboard"))
    return render_template("add_property.html")

@app.route("/owner/delete/<int:rid>",methods=["POST"])
@owner_only
def delete_property(rid):
    with connect() as c:
        room=c.execute("SELECT * FROM properties WHERE id=? AND owner_id=?",(rid,session["owner_id"])).fetchone()
        if not room: abort(404)
        for name in json.loads(room["photos"]):
            path=os.path.join(UPLOADS,name)
            if os.path.isfile(path): os.remove(path)
        c.execute("DELETE FROM properties WHERE id=? AND owner_id=?",(rid,session["owner_id"]))
    flash("Your listing was deleted.","success")
    return redirect(url_for("owner_dashboard"))

@app.route("/admin",methods=["GET","POST"])
def admin_login():
    if request.method=="POST":
        with connect() as c:
            a=c.execute("SELECT * FROM admins WHERE username=?",(request.form.get("username",""),)).fetchone()
        if a and check_password_hash(a["password_hash"],request.form.get("password","")):
            session.clear(); session["admin_id"]=a["id"]
            return redirect(url_for("admin_dashboard"))
        flash("Incorrect admin username or password.","danger")
    return render_template("admin_login.html")

@app.route("/admin/dashboard")
@admin_only
def admin_dashboard():
    status=request.args.get("status","Pending")
    if status not in ["Pending","Approved","Rejected"]: status="Pending"
    with connect() as c:
        rooms=c.execute("""SELECT p.*,o.name owner_name,o.mobile owner_mobile FROM properties p
            JOIN owners o ON o.id=p.owner_id WHERE p.status=? ORDER BY p.id DESC""",(status,)).fetchall()
    return render_template("admin_dashboard.html",rooms=rooms,status=status)

@app.route("/admin/<int:rid>/<action>",methods=["POST"])
@admin_only
def admin_action(rid,action):
    target={"approve":"Approved","reject":"Rejected"}.get(action)
    if not target: abort(404)
    with connect() as c: c.execute("UPDATE properties SET status=? WHERE id=?",(target,rid))
    flash("Listing "+target.lower()+".","success")
    return redirect(url_for("admin_dashboard"))

@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for("home"))

@app.errorhandler(413)
def too_big(_):
    flash("Total photo upload is over 12 MB. Please choose smaller photos.","danger")
    return redirect(request.referrer or url_for("add_property"))

init_db()

if __name__ == "__main__":
   app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
