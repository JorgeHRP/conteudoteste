# Protótipo Flask + Supabase 🚀

### Passos para rodar:

1. Criar ambiente virtual (opcional, mas recomendado):
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate   # Windows
   ```

2. Instalar dependências:
   ```bash
   pip install -r requirements.txt
   ```

3. Definir variáveis de ambiente:
   ```bash
   export SUPABASE_URL="https://seu-projeto.supabase.co"
   export SUPABASE_KEY="sua-chave-aqui"
   ```

4. Rodar:
   ```bash
   python app.py
   ```

➡️ Endpoints:
- `/` → página inicial  
- `/usuarios` (GET) → lista usuários  
- `/usuarios` (POST) → adicionar usuário  
