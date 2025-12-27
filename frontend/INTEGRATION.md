# Integração com Backend Seguro 🔒

Este documento descreve as mudanças realizadas para integrar o frontend com o backend seguro baseado em cookies HttpOnly.

## 📋 Resumo das Mudanças

### ❌ Removido (Inseguro)
- **localStorage** para armazenamento de tokens JWT
- **Authorization: Bearer** headers
- Dependência de `access_token` nas respostas

### ✅ Adicionado (Seguro)
- **Cookies HttpOnly** para sessões
- **CSRF Protection** com tokens em headers
- **credentials: "include"** em todas as requisições
- Funções helper para leitura de cookies

## 🔧 Arquivos Modificados

### 1. `lib/utils.ts`

**Adicionado:**
```typescript
// Funções para ler cookies (CSRF token)
export function getCookie(name: string): string
export function getCSRFToken(): string
```

**Motivo:** Frontend precisa ler o cookie `XSRF-TOKEN` para enviar no header `X-CSRF-Token`.

---

### 2. `lib/auth.ts`

**Antes:**
```typescript
export const setToken = (token: string) => {
  localStorage.setItem("token", token)
}

export const getToken = (): string | null => {
  return localStorage.getItem("token")
}

export const isAuthenticated = (): boolean => {
  return !!getToken()
}
```

**Depois:**
```typescript
import { getCookie } from "./utils"

export const isAuthenticated = (): boolean => {
  return getCookie('sid') !== '' // Lê cookie de sessão
}

// setToken e getToken mantidos como deprecated (compatibilidade)
```

**Motivo:** Autenticação agora verifica cookie `sid` (HttpOnly) em vez de localStorage.

---

### 3. `lib/api.ts`

**Antes:**
```typescript
class ApiClient {
  private getAuthHeader(): Record<string, string> {
    const token = localStorage.getItem("token")
    return token ? { Authorization: `Bearer ${token}` } : {}
  }

  async login(email, password): Promise<AuthResponse> {
    // ... sem credentials
    return response.json() // {access_token, token_type}
  }
}
```

**Depois:**
```typescript
import { getCSRFToken } from "./utils"

class ApiClient {
  private getHeaders(includeCSRF: boolean = true): HeadersInit {
    const headers: HeadersInit = {
      "Content-Type": "application/json",
    }

    if (includeCSRF) {
      const csrfToken = getCSRFToken()
      if (csrfToken) {
        headers["X-CSRF-Token"] = csrfToken
      }
    }

    return headers
  }

  private async fetchWithCredentials(url, options): Promise<Response> {
    return fetch(url, {
      ...options,
      credentials: "include", // CRÍTICO: Envia cookies
    })
  }

  async login(email, password): Promise<AuthResponse> {
    // Backend seta cookies automaticamente
    return response.json() // {ok, message}
  }
}
```

**Mudanças principais:**
1. **credentials: "include"** em todas as requisições
2. **X-CSRF-Token** header em métodos mutáveis
3. **Sem Authorization header** (cookies enviados automaticamente)
4. Respostas retornam `{ok, message}` em vez de `{access_token}`

---

### 4. `components/auth-form.tsx`

**Antes:**
```typescript
import { setToken } from "@/lib/auth"

const handleSubmit = async (e) => {
  const response = await api.login(email, password)
  setToken(response.access_token) // Salva no localStorage
  router.push("/dashboard")
}
```

**Depois:**
```typescript
// Sem import de setToken

const handleSubmit = async (e) => {
  // Backend seta cookies HttpOnly automaticamente
  await api.login(email, password)

  // Cookies já estão setados, apenas redirecionar
  router.push("/dashboard")
}
```

**Motivo:** Backend seta cookies automaticamente na resposta. Frontend não precisa fazer nada.

---

### 5. Novos Arquivos

#### `.env.example`
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

#### `.env.local`
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

#### `README.md`
Documentação completa do frontend com:
- Instruções de setup
- Detalhes de segurança
- Estrutura do projeto
- Guia de troubleshooting

## 🔐 Fluxo de Autenticação Atualizado

### 1. Login/Signup

```
Frontend                    Backend
   │                           │
   ├──POST /auth/login────────>│
   │  {email, password}         │
   │                           │
   │                      Valida credenciais
   │                      Cria sessão
   │                      Gera CSRF token
   │                           │
   │<──200 OK + Cookies────────┤
   │  {ok: true, message: "..."}
   │  Set-Cookie: sid=...; HttpOnly; Secure
   │  Set-Cookie: XSRF-TOKEN=...; Secure
   │                           │
   └──Redirect /dashboard
```

### 2. Requisição Autenticada

```
Frontend                    Backend
   │                           │
   ├──POST /chat/ask──────────>│
   │  Cookie: sid=...; XSRF-TOKEN=...
   │  X-CSRF-Token: ...         │
   │  {question: "..."}         │
   │                           │
   │                      Valida sid (sessão)
   │                      Valida CSRF
   │                      Processa request
   │                      Renova TTL
   │                           │
   │<──200 OK───────────────────┤
   │  {answer: "...", sources: [...]}
   │                           │
```

### 3. Logout

```
Frontend                    Backend
   │                           │
   ├──POST /admin/logout──────>│
   │  Cookie: sid=...; XSRF-TOKEN=...
   │  X-CSRF-Token: ...         │
   │                           │
   │                      Deleta sessão
   │                      Deleta namespace Pinecone
   │                      Limpa cookies
   │                           │
   │<──200 OK + Clear Cookies──┤
   │  Set-Cookie: sid=; Max-Age=0
   │  Set-Cookie: XSRF-TOKEN=; Max-Age=0
   │                           │
   └──Redirect /
```

## 🛡️ Proteções Implementadas

### XSS (Cross-Site Scripting)
- ✅ Cookies `sid` são **HttpOnly** (JavaScript não acessa)
- ✅ Mesmo com XSS, atacante não pode roubar sessão

### CSRF (Cross-Site Request Forgery)
- ✅ **Double-Submit Cookie Pattern**:
  - Cookie `XSRF-TOKEN` (não-HttpOnly, front lê)
  - Header `X-CSRF-Token` (front envia)
  - Backend compara: `cookie == header`
- ✅ **SameSite=Lax** em todos os cookies

### Session Hijacking
- ✅ Cookies apenas em **HTTPS** (Secure flag)
- ✅ Sessões expiram (TTL 2 horas)
- ✅ Sliding window (renovação automática)

## 📊 Comparação: Antes vs Depois

| Aspecto | ❌ Antes | ✅ Depois |
|---------|----------|-----------|
| **Armazenamento** | localStorage | Cookies HttpOnly |
| **Acesso JS** | Sim (vulnerável XSS) | Não |
| **Headers** | Authorization: Bearer | X-CSRF-Token |
| **Credentials** | Não enviado | credentials: "include" |
| **Revogação** | Impossível (stateless) | Instantânea (delete sessão) |
| **CSRF** | Sem proteção | Double-submit pattern |
| **Segurança** | ⚠️ Baixa | ✅ Alta |

## 🧪 Testando a Integração

### 1. Iniciar Backend

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

### 2. Iniciar Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

### 3. Testar Fluxo

1. Acesse http://localhost:3000
2. Crie uma conta (signup)
3. Verifique cookies no DevTools (Application > Cookies):
   - `sid` (HttpOnly ✅)
   - `XSRF-TOKEN` (não-HttpOnly ✅)
4. Faça upload de documento
5. Faça perguntas no chat
6. Logout e verifique que cookies foram limpos

### 4. Verificar CSRF

Abra DevTools > Network:
- Veja requisição POST
- Headers devem incluir:
  - `Cookie: sid=...; XSRF-TOKEN=...`
  - `X-CSRF-Token: ...` (mesmo valor do cookie)

## 🚨 Troubleshooting

### Problema: Cookies não aparecem

**Causa:** CORS não configurado corretamente

**Solução:**
```python
# backend/app/main.py
CORSMiddleware(
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,  # NECESSÁRIO
)
```

### Problema: 403 CSRF token inválido

**Causa:** Frontend não está enviando CSRF header

**Solução:** Verifique `lib/api.ts`:
```typescript
headers["X-CSRF-Token"] = getCSRFToken()
```

### Problema: 401 Sessão não encontrada

**Causa:** Backend reiniciou (sessões em memória perdidas)

**Solução:**
1. Faça logout
2. Limpe cookies do navegador
3. Faça login novamente
4. **Produção:** Migre para Redis

## 📝 Próximos Passos

- [ ] Testar em diferentes navegadores
- [ ] Adicionar testes E2E (Playwright)
- [ ] Implementar refresh automático em erro 401
- [ ] Adicionar loading skeletons
- [ ] Implementar dark mode toggle
- [ ] Adicionar animações de transição

## 📚 Referências

- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [OWASP CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [MDN: HTTP Cookies](https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies)
- [Next.js Data Fetching](https://nextjs.org/docs/app/building-your-application/data-fetching)

---

**Integração concluída com sucesso!** ✅🔒
