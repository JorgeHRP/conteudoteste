from supabase import create_client
from dotenv import load_dotenv
import os, bcrypt

# carregar variáveis
load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

supabase = create_client(url, key)

# dados do usuário
nome = "jorge"
senha = "teste123"
empresa = "faculdade prado"

# gerar hash seguro
senha_hash = bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

# inserir no Supabase
response = supabase.table("usuarios").insert({
    "nome": nome,
    "senha": senha_hash,
    "empresa": empresa
}).execute()

print("Usuário inserido:", response.data)
