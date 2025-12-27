# Changelog

## v2.0.0 - Migração para Autenticação Segura (2025-10-05)

### 🔒 Mudanças de Segurança (Breaking Changes)

#### ❌ Removido (Vulnerável)
- **localStorage**: Armazenamento de JWT no navegador
- **JWT no body**: Tokens enviados no corpo das requisições
- **Autenticação stateless**: Sem possibilidade de revogação

#### ✅ Adicionado (Seguro)
- **Cookies HttpOnly**: Session ID inacessível ao JavaScript
- **CSRF Protection**: Double-submit cookie pattern
- **Sessões opacas**: IDs no client, dados no servidor
- **Session Store**: Gerenciamento de sessões (memória/Redis)
- **Security Headers**: CSP, X-Frame-Options, X-Content-Type-Options
- **Sliding Window**: Renovação automática de sessões ativas

### Backend

#### Novos Arquivos
- `app/session_store.py` - Gerenciamento de sessões
- `SECURITY.md` - Guia de segurança completo

#### Arquivos Modificados

**`app/security.py`**
```diff
- import jwt
- def create_access_token(sub: str) -> str:
-     return jwt.encode({"sub": sub}, SECRET, algorithm="HS256")

+ from .session_store import create_session, get_session, delete_session
+ def create_auth_response(response: Response, user_id: str):
+     sid, csrf = create_session(user_id)
+     response.set_cookie("sid", sid, httponly=True, secure=True, samesite="lax")
+     response.set_cookie("XSRF-TOKEN", csrf, httponly=False, secure=True, samesite="lax")
```

**`app/routers/auth.py`**
```diff
- return {"access_token": token, "token_type": "bearer"}
+ create_auth_response(response, str(user.id))
+ return {"ok": True, "message": "Login realizado com sucesso"}
```

**`app/routers/ingest.py`**
```diff
- def upload(file: UploadFile, token: str = Form(...)):
-     uid = decode_token(token)

+ def upload(request: Request, file: UploadFile, user_id: str = Depends(require_auth)):
+     # user_id já validado e extraído da sessão
```

**`app/main.py`**
```diff
+ # Middleware de segurança
+ @app.middleware("http")
+ async def security_headers(request, call_next):
+     response.headers["Content-Security-Policy"] = "..."
+     response.headers["X-Frame-Options"] = "DENY"
+     ...
```

### Frontend

#### Novos Arquivos
- `src/utils.ts` - getCookie, getCSRFToken, isAuthenticated

#### Arquivos Modificados

**`src/api.ts`**
```diff
- export const api = axios.create({
-   baseURL: "http://localhost:8000"
- })

+ export const api = axios.create({
+   baseURL: "http://localhost:8000",
+   withCredentials: true  // CRÍTICO: envia cookies
+ })
+
+ // Interceptor CSRF
+ api.interceptors.request.use(config => {
+   if (["post", "put", "patch", "delete"].includes(config.method)) {
+     config.headers["X-CSRF-Token"] = getCSRFToken()
+   }
+   return config
+ })
```

**`src/App.tsx`**
```diff
- const [token, setToken] = useState(localStorage.getItem("token"))
- const onAuth = (t: string) => {
-   localStorage.setItem("token", t)
-   setToken(t)
- }

+ const [isAuth, setIsAuth] = useState(isAuthenticated())
+ const onAuth = () => {
+   setIsAuth(true)  // Cookies setados pelo backend
+ }
```

**`src/pages/Login.tsx`**
```diff
- const { data } = await api.post("/auth/login", { email, password })
- onAuth(data.access_token)

+ await api.post("/auth/login", { email, password })
+ onAuth()  // Sem token, apenas notifica autenticação
```

**`src/pages/Dashboard.tsx`**
```diff
- function UploadZone({ token }: { token: string }) {
-   const fd = new FormData()
-   fd.append("token", token)

+ function UploadZone() {
+   const fd = new FormData()
+   // Cookies enviados automaticamente, CSRF no header
```

### Migração

#### Se você estava usando v1.0.0 (JWT)

1. **Backend**: Dados de sessão não são migráveis (todos usuários precisarão fazer login novamente)
2. **Frontend**: Limpe localStorage: `localStorage.clear()`
3. **Ambiente**: Adicione `SESSION_TTL_MINUTES` no `.env`

#### Compatibilidade

- ❌ **Não compatível** com versão anterior
- ⚠️ Todos usuários precisarão fazer login novamente
- ✅ Dados do Pinecone (documentos indexados) permanecem intactos

### Melhorias de Performance

- Session lookups otimizados (O(1) com Redis)
- Sliding window reduz logins desnecessários
- CSRF validation apenas em métodos mutáveis

### Próximas Versões

#### v2.1.0 (Planejado)
- [ ] Migração para Redis (produção)
- [ ] Rate limiting por IP
- [ ] Logs estruturados

#### v2.2.0 (Planejado)
- [ ] 2FA (TOTP)
- [ ] Logout de todas as sessões
- [ ] Session device tracking

#### v3.0.0 (Futuro)
- [ ] OAuth2 (Google, GitHub)
- [ ] Refresh tokens rotativos
- [ ] WebAuthn (passkeys)

---

## v1.0.0 - Release Inicial (Depreciado)

### Funcionalidades
- Autenticação JWT (localStorage) ⚠️ **Vulnerável a XSS**
- Upload de documentos
- Crawler de URLs
- Chat RAG com Pinecone
- Frontend React

### Problemas de Segurança
- ❌ JWT em localStorage (XSS)
- ❌ Sem proteção CSRF
- ❌ Tokens sem revogação
- ❌ Sem security headers

**Status**: Depreciado em favor de v2.0.0
