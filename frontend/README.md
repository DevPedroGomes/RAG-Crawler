# RAG Chatbot Frontend 🎨

Modern, secure Next.js frontend for the PG Multiuser RAG application with shadcn/ui components.

## 🔒 Security Features

This frontend implements **secure authentication** using:

✅ **HttpOnly Cookies** - Session tokens inaccessible to JavaScript (XSS protection)
✅ **CSRF Protection** - Automatic CSRF token in request headers
✅ **No localStorage** - No sensitive data in browser storage
✅ **Credentials: include** - Automatic cookie transmission
✅ **Modern UI** - Built with Next.js 15 and React 19

## 🎨 Tech Stack

- **Next.js 15** - React framework with App Router
- **React 19** - Latest React with Server Components
- **shadcn/ui** - High-quality component library
- **Radix UI** - Accessible component primitives
- **Tailwind CSS** - Utility-first CSS framework
- **TypeScript** - Type safety

## 📋 Prerequisites

- Node.js 18+ or 20+
- pnpm (recommended) or npm
- Backend API running on port 8000

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Using pnpm (recommended)
pnpm install

# Or using npm
npm install
```

### 2. Configure Environment

```bash
cp .env.example .env.local
```

Edit `.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Run Development Server

```bash
# Using pnpm
pnpm dev

# Or using npm
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## 📁 Project Structure

```
frontend/
├── app/
│   ├── dashboard/
│   │   └── page.tsx          # Dashboard page
│   ├── globals.css            # Global styles
│   ├── layout.tsx             # Root layout
│   └── page.tsx               # Home/Login page
├── components/
│   ├── ui/                    # shadcn/ui components
│   ├── auth-form.tsx          # Login/Signup form
│   ├── upload-section.tsx     # File upload & URL indexing
│   └── chat-section.tsx       # RAG chat interface
├── lib/
│   ├── api.ts                 # API client (with CSRF)
│   ├── auth.ts                # Auth utilities (cookies)
│   └── utils.ts               # Helper functions
├── hooks/                     # Custom React hooks
├── public/                    # Static assets
└── styles/                    # Additional styles
```

## 🔐 Authentication Flow

### Login/Signup

```typescript
// Backend sets HttpOnly cookies automatically
await api.login(email, password)
// Cookies: sid (HttpOnly), XSRF-TOKEN

// Redirect to dashboard
router.push("/dashboard")
```

### Authenticated Requests

```typescript
// Cookies sent automatically
// CSRF token added to headers
await api.uploadFile(file)
await api.ask(question)
```

### Logout

```typescript
// Backend clears cookies and deletes namespace
await api.logout()
router.push("/")
```

## 🎨 Key Components

### AuthForm

Login and signup form with validation and error handling.

```tsx
<AuthForm />
```

**Features:**
- Email/password validation
- Toggle between login and signup
- Error display
- Loading states

### UploadSection

Upload documents and index URLs.

```tsx
<UploadSection />
```

**Features:**
- File upload (PDF, TXT)
- URL crawling
- Progress indicators
- Success/error feedback

### ChatSection

RAG chat interface with source display.

```tsx
<ChatSection />
```

**Features:**
- Question input
- AI-powered answers
- Source attribution
- Reset knowledge base

## 🛠️ API Integration

The frontend communicates with the backend using secure, cookie-based authentication.

### API Client (`lib/api.ts`)

```typescript
class ApiClient {
  // All methods use credentials: "include"
  // CSRF token automatically added to headers

  async login(email, password)
  async signup(email, password)
  async uploadFile(file)
  async crawlUrl(url)
  async ask(question)
  async reset()
  async logout()
}
```

### Security Headers

All POST/PUT/PATCH/DELETE requests include:

```typescript
{
  "Content-Type": "application/json",
  "X-CSRF-Token": getCSRFToken() // From XSRF-TOKEN cookie
}
```

## 🎨 Styling

### Tailwind CSS

The project uses Tailwind CSS with a custom configuration:

```css
/* Dark mode support */
@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 240 10% 3.9%;
    /* ... more CSS variables */
  }

  .dark {
    --background: 240 10% 3.9%;
    --foreground: 0 0% 98%;
    /* ... more CSS variables */
  }
}
```

### Custom Components

All UI components follow the shadcn/ui pattern:

```tsx
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"

<Button variant="outline" size="sm">
  Click me
</Button>
```

## 🧪 Development

### Adding New Components

```bash
# Add shadcn/ui components
npx shadcn@latest add button
npx shadcn@latest add card
npx shadcn@latest add input
```

### Type Checking

```bash
pnpm tsc --noEmit
# or
npm run type-check
```

### Linting

```bash
pnpm lint
# or
npm run lint
```

## 📦 Build for Production

```bash
# Build the application
pnpm build
# or
npm run build

# Start production server
pnpm start
# or
npm start
```

## 🔧 Configuration Files

### `next.config.mjs`

Next.js configuration with optimizations.

### `tailwind.config.ts`

Tailwind CSS configuration with custom theme.

### `tsconfig.json`

TypeScript configuration with strict mode enabled.

### `components.json`

shadcn/ui configuration for component installation.

## 🐛 Troubleshooting

### Cookies Not Working

**Issue:** Session cookies not being sent

**Solutions:**
1. Check CORS settings in backend
2. Ensure `credentials: "include"` is set
3. Verify `allow_credentials=True` in backend
4. Use same domain or proper CORS origins

### CSRF Token Missing

**Issue:** 403 CSRF token invalid

**Solutions:**
1. Check if `XSRF-TOKEN` cookie exists
2. Verify `X-CSRF-Token` header is sent
3. Clear browser cookies and login again
4. Ensure backend sets CSRF cookie

### API Errors

**Issue:** Network errors or 500 responses

**Solutions:**
1. Verify backend is running on port 8000
2. Check `NEXT_PUBLIC_API_URL` environment variable
3. Check browser console for CORS errors
4. Verify backend CORS configuration

## 📚 Learn More

- [Next.js Documentation](https://nextjs.org/docs)
- [shadcn/ui Documentation](https://ui.shadcn.com)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [Radix UI Documentation](https://www.radix-ui.com/docs/primitives)

## 🤝 Contributing

Contributions are welcome! Please ensure:

- TypeScript types are correct
- Components follow shadcn/ui patterns
- Security best practices are maintained
- Cookies are used (no localStorage for auth)

## 📝 License

MIT

---

**Built with security and user experience in mind** 🔒✨
