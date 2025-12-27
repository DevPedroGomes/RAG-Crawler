# Guia de Segurança 🔒

Este documento descreve as medidas de segurança implementadas na aplicação PG Multiuser RAG.

## Resumo Executivo

Esta aplicação implementa o **padrão moderno e robusto** de autenticação web, seguindo as recomendações da OWASP e as melhores práticas da indústria.

### ❌ O que NÃO fazemos

- ❌ **localStorage** para tokens (vulnerável a XSS)
- ❌ **JWT no body/header** acessível ao JavaScript
- ❌ Tokens longos sem possibilidade de revogação
- ❌ Autenticação stateless pura (dificulta revogação)

### ✅ O que fazemos

- ✅ **Cookies HttpOnly** (JavaScript não acessa)
- ✅ **CSRF Protection** (double-submit pattern)
- ✅ **Sessões opacas** com store no servidor
- ✅ **Security Headers** (CSP, X-Frame-Options, etc.)
- ✅ **Sliding window** (renovação automática)
- ✅ **Namespace isolation** por usuário

## Arquitetura de Segurança

### 1. Autenticação: Sessões Opacas

#### Backend
```python
# Ao fazer login
def create_auth_response(response, user_id):
    sid, csrf = create_session(user_id)  # Gera session ID opaco

    # Cookie HttpOnly - JavaScript NÃO acessa
    response.set_cookie(
        "sid", sid,
        httponly=True,   # XSS protection
        secure=True,     # HTTPS only
        samesite="lax"   # CSRF protection
    )

    # Cookie CSRF - JavaScript lê e envia em header
    response.set_cookie(
        "XSRF-TOKEN", csrf,
        httponly=False,  # JS precisa ler
        secure=True,
        samesite="lax"
    )
```

#### Frontend
```typescript
// Axios envia cookies automaticamente
api.defaults.withCredentials = true

// Interceptor adiciona CSRF header
config.headers["X-CSRF-Token"] = getCSRFToken()
```

### 2. Proteção CSRF

**Double-Submit Cookie Pattern:**

1. Backend seta cookie `XSRF-TOKEN` (não-HttpOnly)
2. Frontend lê cookie e envia em header `X-CSRF-Token`
3. Backend compara: `cookie == header`

```python
def validate_csrf(request):
    csrf_cookie = request.cookies.get("XSRF-TOKEN")
    csrf_header = request.headers.get("X-CSRF-Token")

    if csrf_cookie != csrf_header:
        raise HTTPException(403, "CSRF token inválido")
```

**Aplicado em:** POST, PUT, PATCH, DELETE

### 3. Proteção XSS

#### Cookies HttpOnly
- Token de sessão **nunca** acessível ao JavaScript
- Mesmo com XSS, atacante não pode roubar sessão

#### Content Security Policy
```http
Content-Security-Policy:
    default-src 'self';
    script-src 'self' 'unsafe-inline';
    style-src 'self' 'unsafe-inline';
    frame-ancestors 'none';
```

#### Input Sanitization
- Validação com Pydantic no backend
- Escape automático no React

### 4. Security Headers

Adicionados automaticamente pelo middleware:

```http
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: accelerometer=(), camera=(), ...
```

### 5. Gerenciamento de Sessões

#### Armazenamento
- **Dev**: Memória (dicionário Python)
- **Prod**: Redis (recomendado)

#### Características
- **TTL**: 2 horas (configurável)
- **Sliding Window**: Renova a cada request
- **Revogação**: Instantânea (delete no store)
- **Cleanup**: Remoção automática de sessões expiradas

```python
# Sessão típica
{
    "user_id": "123",
    "csrf_token": "abc...",
    "expires_at": 1234567890,
    "created_at": 1234565000
}
```

### 6. Isolamento de Dados

#### Pinecone Namespaces
Cada usuário tem namespace único no Pinecone:

```python
namespace = str(user_id)  # "123", "456", etc.

# Indexação isolada
pinecone.upsert(vectors, namespace=user_id)

# Query isolada
pinecone.query(embedding, namespace=user_id)

# Limpeza no logout
pinecone.delete(delete_all=True, namespace=user_id)
```

#### Garantias
- ✅ Usuário A nunca vê dados do usuário B
- ✅ Queries isoladas por namespace
- ✅ Limpeza completa no logout

### 7. Senhas

#### Hash
- **Algoritmo**: bcrypt
- **Rounds**: 12 (padrão passlib)
- **Salting**: Automático

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"])
hash = pwd_context.hash(password)
```

#### Validação
- Sem requisitos mínimos por padrão (adicione se necessário)
- Recomendado: min 8 caracteres, 1 maiúscula, 1 número

### 8. CORS

Configurado para permitir **apenas origins específicos** com credenciais:

```python
CORSMiddleware(
    allow_origins=["http://localhost:5173"],  # Especificar!
    allow_credentials=True,  # Necessário para cookies
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-CSRF-Token"]
)
```

⚠️ **NUNCA** use `allow_origins=["*"]` com `allow_credentials=True`

## Fluxo Completo de Autenticação

### Login
```
1. POST /auth/login {email, password}
2. Backend valida credenciais
3. Backend cria sessão → {sid, csrf}
4. Backend seta cookies HttpOnly
5. Frontend recebe cookies automaticamente
6. Frontend redireciona para dashboard
```

### Request Autenticada
```
1. GET/POST /api/endpoint
2. Browser envia cookies automaticamente
3. Frontend adiciona header X-CSRF-Token
4. Backend valida:
   - Cookie sid existe?
   - Sessão válida (não expirada)?
   - CSRF válido (cookie == header)?
5. Backend processa request
6. Backend renova TTL (sliding window)
```

### Logout
```
1. POST /admin/logout
2. Backend valida sessão + CSRF
3. Backend deleta namespace Pinecone
4. Backend deleta sessão do store
5. Backend limpa cookies (Max-Age=0)
6. Frontend redireciona para login
```

## Desenvolvimento Local

### HTTP vs HTTPS

Por padrão, cookies têm `secure=True` (HTTPS only).

Para desenvolvimento local HTTP:

```python
# backend/app/security.py
response.set_cookie(
    ...,
    secure=False  # ⚠️ APENAS EM DEV
)
```

### Testando CSRF

```bash
# Request SEM CSRF header (deve falhar)
curl -X POST http://localhost:8000/chat/ask \
  -H "Cookie: sid=..." \
  -d '{"question":"test"}'
# → 403 CSRF token inválido

# Request COM CSRF header (deve funcionar)
curl -X POST http://localhost:8000/chat/ask \
  -H "Cookie: sid=...; XSRF-TOKEN=abc123" \
  -H "X-CSRF-Token: abc123" \
  -d '{"question":"test"}'
# → 200 OK
```

## Produção: Checklist

### Obrigatório

- [ ] Migrar session store para **Redis**
- [ ] Usar **HTTPS** (Let's Encrypt, Cloudflare)
- [ ] `secure=True` em TODOS os cookies
- [ ] Origins específicos no CORS (não `*`)
- [ ] Secrets fortes (JWT_SECRET, etc.)
- [ ] Rate limiting (slowapi, nginx)
- [ ] Logs estruturados (structlog)
- [ ] Monitoring (Sentry, Datadog)
- [ ] Backup do banco de dados

### Recomendado

- [ ] 2FA (TOTP)
- [ ] Session fixation protection
- [ ] Geolocation/device tracking
- [ ] Logout de todas as sessões
- [ ] Password reset seguro
- [ ] Account lockout (brute force)
- [ ] Audit logs
- [ ] Pen testing

### Infraestrutura

- [ ] WAF (Web Application Firewall)
- [ ] DDoS protection
- [ ] SSL/TLS A+ (SSL Labs)
- [ ] Secrets em vault (não .env)
- [ ] Network isolation
- [ ] Container scanning

## Vulnerabilidades Mitigadas

### ✅ XSS (Cross-Site Scripting)
- **Mitigação**: Cookies HttpOnly + CSP + Input validation

### ✅ CSRF (Cross-Site Request Forgery)
- **Mitigação**: Double-submit cookies + SameSite=Lax

### ✅ Session Hijacking
- **Mitigação**: Secure cookies + HTTPS + HttpOnly

### ✅ Session Fixation
- **Mitigação**: Nova sessão a cada login

### ✅ SQL Injection
- **Mitigação**: SQLAlchemy ORM + Parametrização

### ✅ Clickjacking
- **Mitigação**: X-Frame-Options: DENY

### ✅ MIME Sniffing
- **Mitigação**: X-Content-Type-Options: nosniff

### ✅ Token Theft via localStorage
- **Mitigação**: Não usamos localStorage!

## Limitações Conhecidas

### Session Store em Memória (Dev)
- ⚠️ Perdas sessões ao reiniciar
- ⚠️ Não escala horizontalmente
- ✅ **Solução**: Migrar para Redis

### Secure=True com HTTP
- ⚠️ Cookies não enviados em dev local HTTP
- ✅ **Solução**: `secure=False` em dev, `secure=True` em prod

### Revogação de Sessões
- ⚠️ Logout não invalida sessões em outros devices
- ✅ **Solução**: Implementar "logout all sessions"

## Referências

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [MDN Web Security](https://developer.mozilla.org/en-US/docs/Web/Security)
- [Token Storage in Browser](https://auth0.com/docs/secure/security-guidance/data-security/token-storage)

## Contato

Para reportar vulnerabilidades de segurança, **NÃO** abra uma issue pública. Entre em contato privadamente.

---

**Última atualização**: 2025-10-05
**Revisão de segurança**: Pendente
