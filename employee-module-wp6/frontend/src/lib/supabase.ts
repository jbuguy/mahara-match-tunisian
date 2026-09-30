import { createClient } from '@supabase/supabase-js'

const url: string | undefined = import.meta.env.VITE_SUPABASE_URL
const publishableKey: string | undefined = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY

if (!url || !publishableKey) {
  throw new Error('VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY must be set in employee-module-wp6/.env')
}

/** Only used for Google login; all data goes through the backend (see lib/api.ts). */
export const supabase = createClient(url, publishableKey, {
  auth: { flowType: 'pkce', detectSessionInUrl: true },
})
