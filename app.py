from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
from dotenv import load_dotenv
import os, bcrypt, requests
from datetime import datetime, timezone
from werkzeug.utils import secure_filename
from flask import send_from_directory


# -----------------------------
# Configurações iniciais
# -----------------------------
load_dotenv()

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Evolution API
BASE_URL = os.getenv("EVOLUTION_BASE_URL", "").rstrip("/")
INSTANCE = os.getenv("EVOLUTION_INSTANCE")
API_KEY  = os.getenv("EVOLUTION_API_KEY")
HEADERS  = {"apikey": API_KEY}

# Flask
app = Flask(__name__)
app.secret_key = "segredo-super-seguro"

# Uploads
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"pdf", "docx", "xlsx"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Lista de documentos (mock em memória)
DOCUMENTOS = []

# -----------------------------
# Helpers
# -----------------------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def short_jid(jid: str) -> str:
    return jid.split("@")[0] if isinstance(jid, str) else jid

def fmt_ts(ts):
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).astimezone().strftime("%d/%m/%Y %H:%M")
    except Exception:
        return ts or "—"

def pick_text(msg_obj: dict) -> str:
    m = (msg_obj or {}).get("message", {}) or {}
    return (
        m.get("conversation")
        or (m.get("extendedTextMessage", {}) or {}).get("text")
        or (m.get("imageMessage", {}) and "[imagem]")
        or (m.get("documentMessage", {}) and "[documento]")
        or (m.get("videoMessage", {}) and "[vídeo]")
        or "[sem texto]"
    )

def get_chats():
    url = f"{BASE_URL}/chat/findChats/{INSTANCE}"
    r = requests.post(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else data.get("chats", [])

def get_messages(remote_jid: str):
    url = f"{BASE_URL}/chat/findMessages/{INSTANCE}"
    payload = {"where": {"key": {"remoteJid": remote_jid}}}
    r = requests.post(
        url,
        headers={**HEADERS, "Content-Type": "application/json"},
        json=payload,
        timeout=25
    )
    r.raise_for_status()
    data = r.json() or {}
    return (data.get("messages", {}) or {}).get("records", [])

# -----------------------------
# Rotas Flask
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        nome = request.form["nome"]
        senha_digitada = request.form["senha"]

        result = supabase.table("usuarios").select("*").eq("nome", nome).execute()
        if result.data:
            usuario = result.data[0]
            senha_hash = usuario["senha"]

            if bcrypt.checkpw(senha_digitada.encode("utf-8"), senha_hash.encode("utf-8")):
                session["usuario"] = usuario["nome"]
                return redirect(url_for("home"))

        return render_template("login.html", erro="Usuário ou senha inválidos")

    return render_template("login.html")

@app.route("/home")
def home():
    if "usuario" not in session:
        return redirect(url_for("login"))
    return render_template("home.html", usuario=session["usuario"])

@app.route("/dashboard")
def dashboard():
    if "usuario" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html", usuario=session["usuario"])

@app.route("/conversas")
def conversas():
    if "usuario" not in session:
        return redirect(url_for("login"))

    remote_jid = request.args.get("jid")

    # Chats
    chats = []
    try:
        raw_chats = get_chats()
        for c in raw_chats:
            rjid = c.get("remoteJid") or c.get("id")
            if not rjid:
                continue
            chats.append({
                "jid": rjid,
                "jid_short": short_jid(rjid),
                "name": c.get("pushName") or short_jid(rjid),
                "avatar": c.get("profilePicUrl"),
                "updatedAt": fmt_ts(c.get("updatedAt"))
            })
    except Exception as e:
        print("Erro ao buscar chats:", e)

    # Mensagens
    messages = []
    try:
        if remote_jid:
            raw_msgs = get_messages(remote_jid)
            for m in raw_msgs:
                key = (m.get("key") or {})
                messages.append({
                    "fromMe": key.get("fromMe"),
                    "text": pick_text(m),
                    "timestamp": fmt_ts(m.get("messageTimestamp")),
                    "pushName": m.get("pushName")
                })
    except Exception as e:
        print("Erro ao buscar mensagens:", e)

    return render_template(
        "conversas.html",
        usuario=session["usuario"],
        chats=chats,
        messages=messages,
        remote_jid=remote_jid
    )
    

@app.route("/uploads/<filename>")
def download_file(filename):
    if "usuario" not in session:
        return redirect(url_for("login"))
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=True)


@app.route("/uploads", methods=["GET", "POST"])
def uploads():
    if "usuario" not in session:
        return redirect(url_for("login"))

    mensagem = None
    if request.method == "POST":
        observacao = request.form.get("observacao", "")

        if "file" not in request.files:
            mensagem = "Nenhum arquivo selecionado."
        else:
            file = request.files["file"]
            if file.filename == "":
                mensagem = "Nenhum arquivo selecionado."
            elif file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(filepath)

                # Registrar documento na lista
                DOCUMENTOS.append({
                    "arquivo": filename,
                    "usuario": session["usuario"],
                    "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "observacao": observacao
                })

                mensagem = f"Arquivo {filename} enviado com sucesso!"
            else:
                mensagem = "Formato de arquivo não permitido."

    return render_template(
        "uploads.html",
        usuario=session["usuario"],
        mensagem=mensagem,
        documentos=DOCUMENTOS
    )

@app.route("/disparo", methods=["GET", "POST"])
def disparo():
    if "usuario" not in session:
        return redirect(url_for("login"))

    sucesso = None
    if request.method == "POST":
        sucesso = "Disparo enviado com sucesso!"

    return render_template("disparo.html", usuario=session["usuario"], sucesso=sucesso)

@app.route("/perfil", methods=["GET", "POST"])
def perfil():
    if "usuario" not in session:
        return redirect(url_for("login"))

    dados = {
        "nome": session["usuario"],
        "email": "usuario@exemplo.com",
        "empresa": "Faculdade Prado"
    }

    mensagem = None
    if request.method == "POST":
        mensagem = "Informações atualizadas."

    return render_template("perfil.html", usuario=session["usuario"], dados=dados, mensagem=mensagem)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# -----------------------------
# Run
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
