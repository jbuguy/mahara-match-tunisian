# Session 2: Google login

Date: 2026-09-30 · Branch: `feature/wp6-employee-module`

Goal: sign in with Google and sign out. No profile code yet.

## What was built

**Backend**
- `app/auth.py`: the `get_current_user` dependency used by every signed-in endpoint.
  - reads `Authorization: Bearer <token>` (`HTTPBearer(auto_error=False)`, so a missing token gives our own 401)
  - verifies it with PyJWT 2.15's `PyJWKClient` on `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`, which is cached per process (`cache_keys=True`)
  - accepts only `algorithms=["ES256"]`, with audience `authenticated` and issuer `{SUPABASE_URL}/auth/v1`, and requires `exp`, `sub` and `email`
  - 401 (`WWW-Authenticate: Bearer`) for a missing, expired or invalid token; 503 if the JWKS can't be fetched
  - returns `CurrentUser(user, name)`, where `name` is `user_metadata.full_name` (or `name`) from the token
- `app/services/users.py`:
  - `get_or_create_user(db, email)` finds the `users` row by lower-cased email, creates it if missing (role `candidate`, `preferred_language` `fr`) and sets `last_login_at`
  - `has_profile(db, user_id)` checks whether a `candidates` row exists
- `app/routers/me.py`: `GET /api/v1/me` returns `{id, email, name, has_profile}`. The response model is in `app/schemas.py`.
- `tests/test_me.py`: 7 tests that sign tokens with a locally generated ES256 key:
  - a valid token for an existing user
  - a first login (email lower-cased, row created)
  - an expired token
  - a wrong audience
  - a wrong issuer
  - an HS256 token
  - a missing token

  `get_settings`, `get_jwks_client` and `get_db` are overridden, so the tests need no `.env`, network or database. Total: 9 tests.

**Frontend**
- `@supabase/supabase-js` **2.117.2** is installed.
- `src/lib/supabase.ts` creates the client with `{ auth: { flowType: 'pkce', detectSessionInUrl: true } }`. It throws a clear error if either `VITE_SUPABASE_*` value is missing.
- `src/lib/auth-context.ts` holds the context type and `useAuth()`, plus the `displayName(session)` and `initials(name)` helpers.
- `src/components/auth/`:
  - `AuthProvider` provides `session`, `loading`, `signInWithGoogle` and `signOut`, using `getSession()` and `onAuthStateChange`
  - `RequireAuth` sends signed-out users to `/login`
  - `FullPageMessage` shows the logo and a message for loading screens
- `src/lib/api.ts`: `api<T>(path, init)` adds the Bearer token. A 401 calls `signOut({ scope: 'local' })`, so the guard redirects to `/login`. The file also has `getMe()`.
- Pages:
  - `/login` shows the logo, "Ahla ! Bienvenue", one sentence and the gold "Continuer avec Google" button. It redirects to `/` if already signed in.
  - `/auth/callback` waits for the session, then goes to `/`. If sign-in fails, it shows "La connexion a échoué", a grey "Détail : …" line and a "Réessayer" link.
  - Accueil says "Bonjour <first name>" and calls `/me` in the background, which creates the `users` row.
- `src/components/layout/UserBits.tsx`:
  - `SidebarUser` (initials, name and "Se déconnecter") sits at the bottom of the sidebar and the drawer
  - `TopBarUserMenu` sits on the right of the 72px desktop top bar: initials, name and a chevron, opening a menu with "Se déconnecter" (items are 44px high)
- `src/components/ui/dropdown-menu.tsx` was added with the shadcn CLI.
- README has a new "Google login (once)" section.

## Env var names

No new names. `SUPABASE_URL` (backend), `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY` (frontend) are now used, and all of them are set in `.env`.

Supabase dashboard settings, which are not env vars:
- Google provider enabled
- Site URL `http://localhost:5173`
- Redirect URLs include `http://localhost:5173/auth/callback`

## Decisions

- **Where the name comes from:** `users` has no name column, and adding one needs approval. So `/me.name` comes from the token's `user_metadata`, and the UI takes the name and initials straight from the Supabase session so they appear without waiting for the backend.
- **`last_login_at`:** it's updated on every authenticated request, as the session prompt specified, so in practice it means "last seen".
- **User ids:** the id is set in Python (`uuid4`), not left to `gen_random_uuid()`, so it's known without a round trip. Two first requests at the same time (StrictMode runs effects twice in dev) can collide on the unique email; the `IntegrityError` is caught and the row is read again.
- **Test overrides:** `get_settings` and `get_jwks_client` are FastAPI dependencies of `get_current_user` so tests can override them.
- **JWKS outages:** if the keys can't be fetched, the backend returns 503, not 401, so a Supabase hiccup doesn't sign the user out.
- **Sign-out scope:** the sign-out button uses supabase-js's default scope (`global`, which ends this user's other sessions too). The 401 path uses `local`, because the token is already dead.
- **Callback errors:** supabase-js hides callback errors, and says nothing at all when the PKCE verifier is missing. So `/auth/callback` asks `supabase.auth.initialize()` for the error and shows it as "Détail". That's how this session's bug was found.
- **The `cn` package:** shadcn's `add dropdown-menu` imported `cn` from the `cn` package again. It was switched to `@/lib/utils` and the package was uninstalled, as in Session 1.
- **Unknown URLs:** there's no catch-all route, so they show React Router's default error page.

## Known issues

- **Rotate secrets:**
  - the Google OAuth client secret was pasted in chat; create a new one in Google Cloud, save it in Supabase, and delete the old one
  - the database password may have been pasted too (15 characters stuck in front of the secret in Supabase)
  - the downloaded `client_secret_*.json` in Downloads holds the old secret, so delete it
- **Sign-in bug fixed in settings:** the first sign-in failed with "Unable to exchange external code" because the Client Secret saved in Supabase had extra characters in front of it. This was a settings problem, not a code one.
- **Bundle size:** the JS bundle is 665 kB and Vite warns about it (mostly supabase-js). That's fine for local use.
- **"Détail" text:** it's technical, in English and meant for developers. Consider hiding it once login is stable.
- **Lint warnings:** oxlint warns (`only-export-components`) about shadcn's `button.tsx` and `badge.tsx`. Both warnings predate this session.
- **Playwright output:** the browser tool writes `.playwright-mcp/` at the **repo root**, which is outside our folder. It was deleted; if it shows up again, delete it and don't commit it.
- **Browser extensions:** a "Redirect Blocker" extension logged messages during the Google step. It didn't block sign-in, but try with extensions off if sign-in ever stalls.

## What Session 3 should do first

1. Read CLAUDE.md, `01-foundation.md` and this file.
2. Ask me whether the Google secret and the database password have been rotated, and check that sign-in still works (`/me` returns 200 in the backend log).
3. Protect every profile endpoint with `Depends(get_current_user)` and call them from the frontend through `api<T>()`. Use `/me.has_profile` to choose between "create your profile" and showing it on the Profil page.
4. Write `scripts/seed_dev.py` (skills `SK-9001`…, occupations `OC-9001`…), then build the profile API and the Profil page.
