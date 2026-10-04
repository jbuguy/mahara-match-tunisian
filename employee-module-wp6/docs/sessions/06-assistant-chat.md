# Session 6: Profile assistant (text chat)

Date: 2026-09-30 · Branch: `feature/wp6-employee-module`

Goal: "Assistant Mahara", a chat that asks the candidate one question at a time and fills the profile form from answers
in French, Tunisian Derja (Latin or Arabic letters) or Arabic. Text only; voice comes in Session 7. The assistant never
saves anything: the candidate ticks consent and presses "Enregistrer" themselves.

Added during the session at my request, after trying it in the browser:
- the form follows the question: its step changes as soon as the assistant asks about a field on another step
- a skill or job that isn't in our lists stops the chat until the candidate picks a suggestion, writes another word or
  presses "Ignorer"

## What was built

**Backend: `app/services/assistant.py`** (groq 1.7.0)
- `get_groq_client`: FastAPI dependency. It returns one cached `groq.Groq` client (timeout 30 s, 1 SDK retry), or 503
  with a French message when `GROQ_API_KEY` is missing.
- `ask_assistant()` sends Groq:
  - the system prompt
  - a second system message: the form's state plus which language to reply in
  - the last 8 messages

  It returns the reply, the checked updates, `asking` and `done`.
- The form's state is `{"full_name": "Amine", "phone": "filled", "governorate": "Sousse", "skills": ["Soudure 3/4"]}`
  followed by `Still empty: …`. The phone number itself is never sent to Groq, only whether it's filled.
- `candidate_language()` reads the candidate's last message that has words in it:
  - mostly Arabic letters → Arabic letters
  - Latin letters with Derja markers (digits inside words like `na3ref`, `9bal`; words like `esmi`, `barcha`) →
    Derja in Latin letters
  - French words → French

  The matching hint is added to the state message.
- `_complete()`: one JSON-mode call. Groq's `json_validate_failed` (the model wrote plain text) is retried once.
  Errors become `AssistantUnavailable`:
  - rate limit → 429, "Un instant, réessayez dans quelques secondes."
  - any other Groq error or unusable JSON → 502, "Désolé, l'assistant n'a pas pu répondre. Réessayez, ou remplissez
    le formulaire vous-même."
- `parse_updates()` validates the model's `updates` with the Pydantic model `ModelUpdates`, **field by field and list
  item by list item**. Whatever doesn't fit is dropped and the rest is kept. Keys that aren't form fields (e.g.
  `consent`) are ignored.
- `resolve_updates()` turns names into the form's shape (the same shape as the CV draft):
  - **Skills and desired jobs:** the CV import's matching (`find_skills`, `words`) against the catalog. If nothing is
    found, the first entry whose label contains the name is used ("informatique" → "informatique de base").
  - **Loading the lists:** each list is read in one query, and only when the answer names something.
  - **Occupations:** each part of "Soudeur / Soudeuse" counts as a search term.
  - **Governorates:** a fixed table of the 24 codes with French and Arabic names plus common spellings ("Sfaks",
    "Sousa", "9ayrawen", "el kef"). Arabic is compared without "ال", with ة read as ه. A test checks the table still
    matches the database.
  - **Skill levels** are 1-4, from a number or the candidate's words:
    - 1: chwaya, un peu
    - 2: normal, moyen
    - 3: behi, bien
    - 4: barcha, expert, très bien

    With a negation, a high level becomes 1 ("mouch barcha", "pas très bien"). Unknown words give 2, the form's default.
  - **Phone:** it must be a Tunisian number and is written like the CV import does (`22 345 678`). Anything else is
    dropped.
  - **Languages:** an ISO code or a name ("français" → `fr`); an unknown level becomes `intermediate`.
- `clarify_unmatched()`: when a skill or job matches nothing, one more small call gets:
  - the missing names
  - our list for that kind
  - the candidate's last message

  Its reply replaces the first one, so the chat doesn't move on. The reply names what wasn't found, suggests up to 3
  close items or says none is close, and asks the candidate to pick one, write another word, or press "Ignorer".
  - Suggestions are kept only if they are in our list (by label, alternative label or a short form of the label) and
    are returned under our label.
  - If this call fails, a fixed "not found" message is used, in French, Derja or Arabic.
  - Matched items from the same answer are still returned.
- `assistant_turn()` runs one full turn for the router.

**Backend: `POST /api/v1/me/assistant/chat`** (`app/routers/assistant.py`)
- It only checks the token (`get_token_claims`). The database is only touched to read the skills/occupations lists.
  Nothing is saved and conversations aren't stored.
- Body: `{messages: [{role: user|assistant, content ≤ 1000}] (1-100), draft}`. The draft accepts the form's values and
  ignores keys it doesn't know.
- Answer: `{reply, updates, unmatched, suggestions, asking, done}`.
  - `updates` has the form's fields; `null` means unchanged.
  - `asking` is the form field the reply asks about (`governorate_code`, `skills`, `desired_occupations`…).
  - `suggestions` are labels from our lists.
- Status codes:
  - 503 without a key or when the database fails
  - 429 on Groq's rate limit
  - 502 on other Groq errors
  - 422 for a bad body
  - 401 without login
- `app/config.py`: `groq_api_key`, `groq_model` (default `openai/gpt-oss-120b`). `requirements.txt`: `groq`.

**Frontend**
- `src/lib/api.ts`: `askAssistant(messages, draft)` sends the last 8 messages, plus the types.
- `src/components/profile/assistant-updates.ts`:
  - `toAssistantDraft(values)`
  - `mergeAssistantUpdates(values, updates)`, which never removes anything:
    - fields are replaced
    - skills and languages get their new level
    - a job with the same title is completed ("soudeur", then "3 ans chez STEG")
    - new items are added, with new skills on top
  - the changed items as keys like `skill:SK-9006`, with their French labels and step
- `ProfileForm` has a `ref` handle (`ProfileFormHandle`):
  - `getValues()`
  - `applyUpdates(updates, asking)`: merges, highlights and changes steps
  - `focusForm()`

  A step change made by the assistant doesn't move focus, so the candidate keeps typing in the chat. The step's top is
  scrolled into view if it was out of sight. Changing step yourself cancels a pending move.
- Following the question: after a reply, the form shows the step of the field it asks about. If the reply also filled
  something on another step, that step is shown first for 1.5 s ("J'ai un BTS" → Niveau d'études glows → step 2 for
  the skills question).
- Gold highlight: `data-flash` on fields and cards, with the `assistant-flash` keyframes in `index.css` (2.4 s; a
  static ring under reduced motion). The first changed field is scrolled into view.
- `src/components/assistant/use-assistant-chat.ts`: the conversation in React state only (lost on refresh). The
  greeting is the fixed text from the session prompt. Each reply's updates go into the form. Errors show as a red note
  with "Réessayer", and the note is never sent to the AI.
- `src/components/assistant/AssistantChat.tsx`:
  - header "Assistant Mahara" and "Fermer"
  - bubbles: the candidate on the right in teal, the assistant on the left on white, both `dir="auto"` so Arabic reads
    right to left
  - a "Rempli : Nom complet, Gouvernorat" line under a reply
  - the "…" indicator while waiting
  - one-tap answers (suggestions, then "Ignorer") under a clarification
  - "Vérifier mon profil" when `done`
  - a 44 px text box and "Envoyer" button
- `src/pages/ProfilFormPage.tsx`: the "Remplir avec l'assistant" button (lucide `MessageCircle`) at the top.
  - **From 1280 px:** a sticky panel on the right of the form, so fields can be seen filling in.
  - **Below 1280 px:** a shadcn Sheet from the bottom (85 % of the height). It doesn't focus the text box on open, so
    the phone keyboard doesn't cover the first question.
  - **The conversation** lives in the page, so closing and reopening keeps it.
  - **"Vérifier mon profil"** closes the chat, scrolls to a gold notice ("Vérifiez vos informations. À l'étape 3,
    cochez la case puis appuyez sur « Enregistrer ».") and focuses the step title.
  - **`state.assistant`** opens the chat on arrival.
- `src/pages/ProfilPage.tsx`: "Remplir avec l'assistant" on the empty state, between "Créer mon profil" (gold) and
  "Importer mon CV".
- Saving is unchanged: the page doesn't send `from_cv`, so a new profile gets `onboarding_path = derja_detailed`. An
  existing CV profile keeps `cv_upload` (Session 3 rule).

**Tests:** 124 in total (72 new in `tests/test_assistant.py`). Groq is replaced by a fake client, so no network or key
is needed.
- A French answer with the real database (rolled back):
  - skill, job and governorate codes
  - the phone written the standard way
  - `consent` ignored
  - JSON mode and model name sent
  - the phone number not sent in the state
  - only the last 8 messages sent
  - no `candidates` row created
- A Derja answer (`esmi Amine, men Sousse` → `TN-51`); `done`; `asking` mapped to form fields.
- Invalid JSON from the model (5 kinds) → 502; invalid updates dropped one by one.
- Missing key → 503; 429 → 429 with the French text; other Groq errors → 502; the `json_validate_failed` retry.
- Language hints; governorate spellings; skill level words; name → code matching without a database; lists not read
  when not needed; the governorate table vs the database.
- Unmatched skill or job: the second call, suggestions filtered to our list, the fallback text in 3 languages.

## The model and the prompts

- Model: `GROQ_MODEL`, default **`openai/gpt-oss-120b`** (open weights, Groq free plan).
- Call settings:
  - `response_format={"type": "json_object"}`
  - `reasoning_effort="medium"`, `include_reasoning=False` (only for `openai/gpt-oss*` models)
  - `temperature=0.3`, `max_completion_tokens=1024`
- Measured: about 1 s and ~1,000 tokens per turn. When a name isn't in our lists: about 2-3 s and ~1,700 tokens.

System prompt (`SYSTEM_PROMPT`):

```text
You are Assistant Mahara, a friendly Tunisian job-profile assistant. You help a job seeker fill their profile form.
Ask ONE short question at a time about the next missing field, in this order: full name, phone, governorate, education level, skills (and how good they are), past jobs (title, employer, how long), jobs they want, languages, a one-sentence "à propos".
The candidate may write French, Tunisian Derja in Latin letters with numbers (3=ع, 7=ح, 9=ق, 5=خ), Derja in Arabic letters, or Modern Standard Arabic. Your reply MUST use the language and script of the candidate's last message, for example:
"esmi Amine" → "Ahla Amine ! Chnowa noumrou telifounek ?"
"إسمي أمين" → "أهلا أمين ! شنوّة نومرو تليفونك ؟"
"Je m'appelle Amine" → "Merci Amine ! Quel est votre numéro de téléphone ?"
Never invent information and never show codes to the candidate. If an answer is unclear, ask again simply. If the candidate has nothing for a field or doesn't want to answer, go to the next one.
If your last message said a skill or job isn't in our lists, don't move on until the candidate gives another word or says to skip it ("Ignorer").
When everything is filled or the candidate says they are done, set done to true and tell them to check the form and press "Enregistrer".

Answer with a JSON object only: {"reply": "...", "updates": {...}, "asking": "phone", "done": false}
"asking" is the field your reply asks about (one of the keys below), or null.
"updates" holds everything the candidate's last message gives or corrects, even fields you didn't ask about ("men Sousse" gives the governorate). Allowed keys:
- full_name, phone, governorate (its French name)
- education_level: none, primary, lower_secondary, baccalaureate, vocational_cap, vocational_btp, vocational_bts, licence, master, engineer or doctorate
- skills: [{"name": "...", "level": 1-4}] (1 chwaya/un peu, 2 normal/moyen, 3 behi/bien, 4 barcha/expert): every skill named, even without a level (then leave "level" out)
- experiences: [{"job_title": "...", "employer": "...", "months": 24}]
- desired_jobs: ["..."]
- languages: [{"code": "ar", "level": "basic|intermediate|fluent|native"}]
- summary: one sentence
Write skill names, job titles and the summary in French.
```

Second system message, for example:

```text
The form now: {"full_name": "Amine", "phone": "filled", "governorate": "Sousse"}
Still empty: education level, skills, past jobs, jobs they want, languages, à propos.
The candidate writes Tunisian Derja in Latin letters: reply in Derja with Latin letters, not in French.
```

Clarification prompt (`CLARIFY_PROMPT`, only when a skill or job isn't in our lists). `{missing}` is for example
`"montage vidéo" (compétence)`, and `{lists}` is `Our skills: Vente; Service client; …`:

```text
You are Assistant Mahara, a friendly Tunisian job-profile assistant.
The candidate named something that isn't in our lists: {missing}.
{lists}
Don't ask the next question yet. In one or two short sentences: name what you didn't find in our list; then suggest up to 3 items of our lists that mean nearly the same thing, naming them, or say that nothing close is in the list; then ask the candidate to write another word (or pick a suggestion) or press "Ignorer" to skip it.
Answer with a JSON object only: {"reply": "...", "suggestions": ["exact names from our lists"]}
```

## Env var names added

- `GROQ_API_KEY` (backend only; never with a `VITE_` prefix) and `GROQ_MODEL` (default `openai/gpt-oss-120b`).
- Both are in `.env.example` with placeholders and in the README table, and both are set in my `.env`.

## Decisions

- **Reasoning "medium", not "low":** with "low", Derja messages often got French replies. "Medium" kept the candidate's
  language on every live test, for about 30 % more tokens.
- **Language hint computed by the backend:** the prompt examples alone weren't enough. A deterministic hint (Arabic
  letters / Derja markers / French words) placed next to the conversation fixed it.
- **`asking` in the answer** (not in the session prompt's `{reply, updates, done}`): the form needs to know which field
  the question is about, to show its step while the assistant asks.
- **Unknown skills/jobs stop the chat:**
  - The model writes its reply before the backend matches names, so it can't know by itself.
  - A second call, made only when something doesn't match, is cheaper than sending our whole list on every turn.
  - "Ignorer" is a message the model understands (the history shows it), so no extra state is needed.
  - Unknown jobs are handled like unknown skills; the session prompt only mentioned skills.
- **Updates validated field by field:** a bad phone number doesn't throw away the name given in the same answer.
- **The phone number isn't sent back to Groq** in the form's state. Only what the candidate types in the chat reaches it.
- **Governorates from a fixed table** (the 24 codes never change, and a test compares the table with the database), so
  a turn that only gives a name and a town needs no database query.
- **One retry on `json_validate_failed`:** the model sometimes answers plain text in JSON mode, and a second try works.
- **Side panel from 1280 px, not 1024 px:** at 1024 px the form would be about 350 px wide and the level buttons don't
  fit. Between 1024 and 1279 px the bottom sheet is used.
- **The form handle uses `ref`** (React 19 ref as a prop) instead of lifting the form's state into the page: the form
  keeps its step, checks and photo logic unchanged.
- **Focus after "Vérifier mon profil"** uses `flushSync` then focus, not `requestAnimationFrame`, which didn't always
  run in the test browser.
- **The backend runs without `--reload` during this session:** `--reload` missed the changes twice on Windows.

## Known issues

- **Free-plan limits:** about 7 turns a minute (8,000 tokens per minute), and daily limits also apply
  (console.groq.com → Settings → Limits). Past the limit the chat says "Un instant…" with "Réessayer".
- **Derja quality:** Derja in Latin letters is sometimes mixed with French words ("Chnowa les expériences ta3ek?").
  Understanding was good in every test; the wording is the weak part.
- **Language detection is simple:** a short Derja answer without markers counts as "no hint", and a mixed message
  with more French words gets French.
- **Clarification wording:** when nothing in our list is close, the reply can still mention "options". The
  one-tap answers then only show "Ignorer".
- **Long conversations:** only the last 8 messages go to the model, so after many corrections it can ask again
  about a field the candidate skipped earlier.
- **Bottom sheet and the phone keyboard:** not checked on a real phone (only a 390 px browser window). The keyboard may
  cover part of the 85 % sheet.
- **Bundle size:** the JS bundle is ~740 kB (Vite warns). Fine locally.
- **Dev servers:** uvicorn `--reload` on Windows often misses changes. Restart the backend after backend edits.

## What Session 7 should do first

1. Read CLAUDE.md and all files in `docs/sessions/`.
2. Check that the key still works: send one message in the chat. If it fails, check `GROQ_API_KEY` in `.env` (don't
   print it).
3. Add a microphone button next to "Envoyer" in `AssistantChat`. Record with MediaRecorder, send the audio to a new
   backend endpoint that calls Groq `whisper-large-v3-turbo`, then pass the text to `useAssistantChat().send()`. The
   rest of the chat stays the same.
