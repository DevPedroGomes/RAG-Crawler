# 🚀 Guia Completo: Como Rodar e Testar Localmente

Vou te guiar **passo a passo** desde zero até ter tudo funcionando. Siga na ordem!

---

## 📋 PARTE 1: Pré-requisitos (Instalar Ferramentas)

### 1.1 Python 3.9+

**Verificar se já tem:**
```bash
python3 --version
# Deve mostrar: Python 3.9.x ou superior
```

**Se não tiver, instalar:**

**macOS:**
```bash
brew install python@3.11
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip
```

**Windows:**
- Baixar de https://www.python.org/downloads/
- Durante instalação, marcar "Add Python to PATH"

---

### 1.2 Node.js 18+ e pnpm

**Verificar se já tem:**
```bash
node --version  # Deve ser v18 ou v20
pnpm --version  # Qualquer versão
```

**Se não tiver:**

**macOS/Linux:**
```bash
# Instalar Node.js via nvm (recomendado)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc  # ou ~/.zshrc
nvm install 20
nvm use 20

# Instalar pnpm
npm install -g pnpm
```

**Windows:**
- Baixar Node.js de https://nodejs.org/
- Depois: `npm install -g pnpm`

---

### 1.3 Redis

**Redis é OBRIGATÓRIO** para a aplicação funcionar com as melhorias implementadas.

#### **Opção A: Docker (MAIS FÁCIL - RECOMENDADO)**

1. **Instalar Docker:**
   - **macOS:** Baixar Docker Desktop de https://www.docker.com/products/docker-desktop
   - **Linux:** `sudo apt install docker.io`
   - **Windows:** Docker Desktop de https://www.docker.com/products/docker-desktop

2. **Rodar Redis:**
```bash
docker run -d --name redis-rag -p 6379:6379 redis:latest

# Verificar se está rodando:
docker ps
# Deve mostrar: redis-rag ... Up ... 0.0.0.0:6379->6379/tcp
```

3. **Testar conexão:**
```bash
docker exec -it redis-rag redis-cli ping
# Deve responder: PONG
```

#### **Opção B: Instalação Local**

**macOS:**
```bash
brew install redis
brew services start redis
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

**Windows:**
- Usar Docker (recomendado) ou WSL2 com Redis

**Verificar:**
```bash
redis-cli ping
# Deve responder: PONG
```

---

## 🔑 PARTE 2: Criar Contas e Obter API Keys

### 2.1 OpenAI API Key

1. **Criar conta:** https://platform.openai.com/signup
2. **Adicionar método de pagamento:** https://platform.openai.com/account/billing/overview
   - Mínimo: $5 USD (você vai gastar ~$0.10 para testar)
3. **Criar API Key:**
   - Ir em: https://platform.openai.com/api-keys
   - Clicar em "Create new secret key"
   - **Nome:** "RAG App Local"
   - **Copiar e guardar:** `sk-proj-...` (só aparece uma vez!)

**Custos estimados para testes:**
- Embeddings (`text-embedding-3-small`): $0.00002 por 1K tokens
- Chat (`gpt-4o-mini`): $0.00015 por 1K tokens entrada
- **Total para 10 documentos + 20 perguntas:** ~$0.10

---

### 2.2 Pinecone API Key

1. **Criar conta:** https://www.pinecone.io/
   - Usar plano **FREE** (suficiente para testes)

2. **Criar API Key:**
   - Ir em: https://app.pinecone.io/organizations/-/projects/-/keys
   - Copiar a API Key (formato: `pcsk_...`)

3. **Criar Index (IMPORTANTE):**

   **Opção A: Via Console (Recomendado para iniciantes)**
   - Ir em: https://app.pinecone.io/
   - Clicar em "Create Index"
   - **Name:** `my-multiuser-index`
   - **Dimensions:** `1536`
   - **Metric:** `cosine`
   - **Cloud:** `AWS`
   - **Region:** `us-east-1`
   - Clicar "Create Index"

   **Opção B: Via Python (a aplicação cria automaticamente)**
   - O código vai criar automaticamente se não existir
   - Mas pode falhar se região não estiver disponível na sua conta

4. **Copiar Host do Index:**
   - Clicar no index criado
   - Copiar o **Host** (formato: `my-multiuser-index-xxxxx.svc.aws-xyz.pinecone.io`)

---

## ⚙️ PARTE 3: Configurar Backend

### 3.1 Navegar para o Backend
```bash
cd backend
```

### 3.2 Criar Virtual Environment
```bash
python3 -m venv venv

# Ativar:
# macOS/Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate

# Deve aparecer (venv) no prompt
```

### 3.3 Instalar Dependências
```bash
pip install --upgrade pip
pip install -r requirements.txt

# Instalar browser do Playwright (para o crawler):
python -m playwright install chromium
```

**Tempo estimado:** 3-5 minutos

### 3.4 Configurar Variáveis de Ambiente

1. **Copiar arquivo de exemplo:**
```bash
cp .env.example .env
```

2. **Editar o arquivo .env:**
```bash
# macOS/Linux:
nano .env

# Ou usar seu editor favorito (VS Code, vim, etc.)
```

3. **Preencher com SUAS credenciais:**
```env
# ==== OpenAI ====
OPENAI_API_KEY=sk-proj-SEU_TOKEN_AQUI

# ==== Pinecone ====
PINECONE_API_KEY=pcsk_SEU_TOKEN_AQUI
PINECONE_INDEX_NAME=my-multiuser-index
PINECONE_INDEX_HOST=my-multiuser-index-xxxxx.svc.aws-xyz.pinecone.io

# ==== Segurança ====
JWT_SECRET=mude-isso-para-algo-aleatorio-em-producao
SESSION_TTL_MINUTES=120

# ==== Redis ====
REDIS_URL=redis://localhost:6379/0

# ==== Crawler ====
HEADLESS=true
BATCH_SIZE=12
CRAWL_DELAY_MS=0
USER_AGENT=pg-multi-crawler/1.0

# ==== Chunking/Embedding ====
EMBEDDING_MODEL=text-embedding-3-small
CHUNK_SIZE=1200
CHUNK_OVERLAP=200
TOP_K=5
```

**IMPORTANTE:** Substituir:
- `SEU_TOKEN_AQUI` pelos valores reais
- `my-multiuser-index-xxxxx.svc.aws-xyz.pinecone.io` pelo host real do Pinecone

4. **Salvar arquivo:**
   - `Ctrl+O` (nano) ou `Cmd+S` (VS Code)
   - `Ctrl+X` (nano) para sair

### 3.5 Rodar Backend

```bash
uvicorn app.main:app --reload --port 8000
```

**Você deve ver:**
```
🚀 [Startup] Iniciando background tasks...
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
[Background Tasks] Scheduler iniciado com sucesso
```

**Se der erro:**

❌ **"ModuleNotFoundError: No module named 'redis'"**
```bash
pip install redis==5.0.1
```

❌ **"redis.exceptions.ConnectionError"**
```bash
# Verificar se Redis está rodando:
docker ps  # ou: redis-cli ping
```

❌ **"openai.OpenAIError: Invalid API key"**
- Verificar se API key está correta no .env
- API key deve começar com `sk-proj-` ou `sk-`

---

## 🎨 PARTE 4: Configurar Frontend

### 4.1 Abrir NOVO TERMINAL (deixar backend rodando)

### 4.2 Navegar para o Frontend
```bash
cd frontend
```

### 4.3 Instalar Dependências
```bash
pnpm install
```

**Tempo estimado:** 2-3 minutos

**Se não tiver pnpm:**
```bash
npm install -g pnpm
# Depois: pnpm install
```

### 4.4 Configurar Variáveis de Ambiente

1. **Criar arquivo .env.local:**
```bash
cp .env.example .env.local
```

2. **Editar:**
```bash
nano .env.local
```

3. **Conteúdo:**
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

4. **Salvar:** `Ctrl+O` → `Ctrl+X`

### 4.5 Rodar Frontend

```bash
pnpm dev
```

**Você deve ver:**
```
  ▲ Next.js 15.2.4
  - Local:        http://localhost:3000
  - Network:      http://192.168.x.x:3000

 ✓ Ready in 2.3s
```

---

## 🧪 PARTE 5: Testar a Aplicação

### 5.1 Acessar Aplicação

1. **Abrir browser:** http://localhost:3000

2. **Você deve ver:**
   - Página de login/signup
   - Logo com ícone de cérebro
   - "RAG Knowledge Assistant"

---

### 5.2 Criar Conta

1. **Preencher formulário:**
   - Email: `teste@example.com`
   - Password: `senha123`

2. **Clicar "Sign up"**

3. **Verificar cookies (DevTools):**
   - Apertar `F12` (abrir DevTools)
   - Aba **Application** → **Cookies** → `http://localhost:3000`
   - Deve ter 2 cookies:
     - ✅ `sid` (HttpOnly ✅, Secure ❌ - ok em HTTP local)
     - ✅ `XSRF-TOKEN` (HttpOnly ❌)

4. **Redireciona para:** http://localhost:3000/dashboard

---

### 5.3 Testar Upload de Documento

1. **Criar arquivo de teste:**
```bash
# Em outro terminal:
cat > /tmp/test.txt << EOF
A Inteligência Artificial (IA) é a simulação de processos de inteligência humana por máquinas, especialmente sistemas computacionais.
Esses processos incluem aprendizado, raciocínio e autocorreção.
Machine Learning é um subcampo da IA que permite que sistemas aprendam e melhorem a partir da experiência sem serem explicitamente programados.
Deep Learning é uma técnica de Machine Learning baseada em redes neurais artificiais com múltiplas camadas.
EOF
```

2. **No dashboard, seção "Upload Documents":**
   - Clicar em **"Select file"**
   - Escolher `/tmp/test.txt`
   - Arquivo será automaticamente enviado

3. **Verificar:**
   - ✅ "test.txt uploaded successfully"
   - ✅ Mensagem de sucesso aparece

4. **No terminal do backend, você deve ver:**
```
INFO: 127.0.0.1:xxxxx - "POST /ingest/upload HTTP/1.1" 200 OK
```

---

### 5.4 Testar Crawl de URL

1. **Na seção "Index URL":**
   - URL: `https://pt.wikipedia.org/wiki/Intelig%C3%AAncia_artificial`
   - Clicar **"Index URL"**

2. **Aguardar (~10-30 segundos):**
   - Playwright vai renderizar a página
   - Extrair texto
   - Gerar embeddings
   - Salvar no Pinecone

3. **Verificar:**
   - ✅ "URL indexed successfully"

**Se der erro de timeout:**
- Aumentar `CRAWL_DELAY_MS` no .env para `5000`
- Ou usar URL mais simples: `https://example.com`

---

### 5.5 Testar Chat (RAG)

1. **Na seção "Chat with Your Knowledge Base":**

2. **Fazer pergunta:**
   ```
   O que é Machine Learning?
   ```

3. **Apertar Enter ou clicar "Ask"**

4. **Aguardar resposta (~5-10 segundos):**

5. **Verificar:**
   - ✅ **Answer:** Resposta baseada no documento
   - ✅ **Sources (2):**
     - Preview do texto relevante
     - Link clicável para a fonte

**Exemplo de resposta esperada:**
```
Answer:
Machine Learning é um subcampo da Inteligência Artificial que permite
que sistemas aprendam e melhorem a partir da experiência sem serem
explicitamente programados.

Sources (2):
┌─────────────────────────────────────────────────┐
│ Machine Learning é um subcampo da IA que        │
│ permite que sistemas aprendam e melhorem a...   │
│ /tmp/test.txt                                   │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│ A Inteligência Artificial (IA) é a simulação... │
│ https://pt.wikipedia.org/wiki/Intelig...        │
└─────────────────────────────────────────────────┘
```

---

### 5.6 Testar SSRF Protection

**Terminal (com cookies da sessão):**

1. **Obter cookies:**
   - DevTools → Application → Cookies
   - Copiar valor de `sid` e `XSRF-TOKEN`

2. **Tentar URL proibida:**
```bash
curl -X POST http://localhost:8000/ingest/crawl \
  -H "Cookie: sid=SEU_SID_AQUI; XSRF-TOKEN=SEU_CSRF_AQUI" \
  -H "X-CSRF-Token: SEU_CSRF_AQUI" \
  -F "url=http://localhost/admin"
```

3. **Resposta esperada (BLOQUEADO):**
```json
{
  "detail": "URL bloqueada por segurança: Acesso a localhost não permitido."
}
```

✅ **SSRF protection funcionando!**

---

### 5.7 Testar Rate Limiting

**Terminal:**

```bash
# Fazer 11 tentativas de login (limite é 10/hora)
for i in {1..11}; do
  echo "Tentativa $i:"
  curl -X POST http://localhost:8000/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"wrong@example.com","password":"wrong"}' \
    -w "\nStatus: %{http_code}\n\n"
done
```

**Resultado esperado:**
- Tentativas 1-10: `{"detail":"Credenciais inválidas"}` (Status 401)
- Tentativa 11: **`Too Many Requests`** (Status 429)

✅ **Rate limiting funcionando!**

---

### 5.8 Testar Sessões Persistentes (Redis)

1. **Com backend rodando e logado no frontend:**
   - Verificar que está funcionando

2. **Parar backend:**
   - Terminal do backend: `Ctrl+C`

3. **Iniciar backend novamente:**
```bash
uvicorn app.main:app --reload --port 8000
```

4. **Voltar ao frontend:**
   - **Recarregar página** (F5)
   - ✅ Ainda está logado!
   - ✅ Pode fazer perguntas normalmente

**ANTES (memória):** Sessão perdida ao reiniciar
**AGORA (Redis):** Sessão persiste ✅

---

### 5.9 Testar Logout Completo

1. **Clicar em "Sign out"**

2. **Verificar:**
   - ✅ Redirecionado para página de login
   - ✅ Cookies deletados (DevTools → Cookies → vazio)

3. **No backend, verificar Pinecone:**
   - Namespace do usuário foi deletado
   - Documentos indexados foram removidos

---

## 🔍 PARTE 6: Verificar Logs e Debugging

### 6.1 Ver Sessões no Redis

```bash
# Conectar ao Redis
docker exec -it redis-rag redis-cli

# Listar todas as keys
KEYS session:*

# Ver detalhes de uma sessão
GET session:ALGUM_SID_AQUI

# Sair
exit
```

### 6.2 Ver Background Task

**No terminal do backend, a cada 30 minutos você verá:**
```
[Session Cleanup] 1 sessões ativas no Redis
```

**Forçar execução manual (Python console):**
```bash
# Em outro terminal (com venv ativado):
python

>>> from app.session_store import cleanup_expired_sessions
>>> cleanup_expired_sessions()
[Session Cleanup] 1 sessões ativas no Redis
1
```

### 6.3 Monitorar Requisições

**Terminal do backend mostra todas as requests:**
```
POST /auth/login - 200 - 0.15s
POST /ingest/upload - 200 - 3.42s
POST /chat/ask - 200 - 5.78s
```

---

## ❌ PARTE 7: Troubleshooting Comum

### Problema 1: "Cannot connect to Redis"

**Solução:**
```bash
# Verificar se Redis está rodando:
docker ps
# ou: redis-cli ping

# Se não estiver, iniciar:
docker start redis-rag
# ou: brew services start redis
```

---

### Problema 2: "OpenAI API Error: Invalid API key"

**Solução:**
1. Verificar `.env`:
```bash
cat backend/.env | grep OPENAI_API_KEY
```

2. API key deve começar com `sk-proj-` ou `sk-`

3. Testar manualmente:
```bash
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer SEU_API_KEY_AQUI"
```

---

### Problema 3: "Pinecone Index Not Found"

**Solução:**
1. Ir em https://app.pinecone.io/
2. Verificar se index existe
3. Copiar **nome exato** do index para `.env`
4. Copiar **host** do index para `PINECONE_INDEX_HOST`

---

### Problema 4: Cookies não aparecem (CORS)

**Solução:**

Verificar `backend/app/main.py`:
```python
allow_origins=[
    "http://localhost:3000",  # Frontend
],
allow_credentials=True,  # OBRIGATÓRIO
```

Verificar `frontend/lib/api.ts`:
```typescript
credentials: "include",  // OBRIGATÓRIO
```

---

### Problema 5: "CSRF token inválido"

**Solução:**
1. Limpar cookies do browser:
   - DevTools → Application → Cookies → Clear All
2. Fazer logout
3. Fazer login novamente

---

### Problema 6: Frontend não conecta ao backend

**Verificar:**
```bash
# Frontend deve ter:
cat frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000

# Testar backend manualmente:
curl http://localhost:8000/health
# Deve retornar: {"ok":true,"status":"healthy"}
```

---

## 📊 PARTE 8: Checklist Final

Após seguir todos os passos, você deve ter:

### Backend (http://localhost:8000)
- ✅ Redis rodando (porta 6379)
- ✅ Backend iniciado com background tasks
- ✅ Health check: http://localhost:8000/health
- ✅ Docs API: http://localhost:8000/docs

### Frontend (http://localhost:3000)
- ✅ Página de login visível
- ✅ Pode criar conta
- ✅ Pode fazer login
- ✅ Dashboard funciona

### Funcionalidades
- ✅ Upload de documento (PDF/TXT)
- ✅ Crawl de URL
- ✅ Chat RAG com sources
- ✅ SSRF protection bloqueia URLs maliciosas
- ✅ Rate limiting funciona (429 após limite)
- ✅ Sessões persistem no Redis
- ✅ Logout limpa tudo

---

## 🎯 Próximos Passos

1. **Testar com documentos reais:**
   - PDFs do seu domínio
   - URLs de documentação

2. **Ajustar parâmetros:**
   - `CHUNK_SIZE` - tamanho dos chunks
   - `TOP_K` - quantos documentos retornar
   - Rate limits conforme necessidade

3. **Monitorar custos:**
   - https://platform.openai.com/usage
   - Embeddings: ~$0.00002/1K tokens
   - Chat: ~$0.00015/1K tokens

4. **Preparar para produção:**
   - Migrar Redis para serviço gerenciado (Redis Cloud, AWS ElastiCache)
   - Configurar HTTPS
   - Usar variáveis de ambiente seguras
   - Adicionar monitoring (Sentry, Datadog)

---

**Dúvidas?** Abra uma issue ou consulte a documentação! 🚀
