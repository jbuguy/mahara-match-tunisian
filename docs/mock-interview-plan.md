# AI Mock Interview: implementation and deployment plan

## Current demo implementation

The candidate mock interview is implemented at `/mock-interview` with private setup consent, occupation/custom/applied-offer targets, 3/5/8 questions, French/Arabic/Tunisian Derja selection, typed answers, optional microphone recording and editable transcription, question playback, saved drafts, delete controls, non-scored coaching feedback, and PDF export. The former prototype state switcher is not part of the app. Video remains a future concept and is not offered as working functionality.

Sessions are owned by a candidate account. Unsaved records expire after 24 hours; explicit saves expire after 30 days. A server retention task removes expired records hourly. Raw audio is processed in memory by the configured transcription service and is not stored. Mock interview answers are not returned by employer, matching, or ministry APIs.

Question and feedback generation uses the shared OpenAI-compatible client configured by `LLM_BASE_URL`, `LLM_MODEL`, and `LLM_API_KEY`. This makes a local inference server compatible with the same API shape a deployment change rather than a feature rewrite. The demo must identify the currently configured provider in its disclosure. When an applied offer is selected, its description and listed skill requirements are sent to that configured model; the user must explicitly consent to that data transfer before starting. Voice transcription currently uses the existing Groq Whisper adapter (`GROQ_API_KEY`), so switching only the LLM endpoint will not make voice fully local. A local transcription adapter is a separate production follow-up.

### To request local inference resources

Before production, choose models that support the required French, Arabic, and Tunisian Derja quality, then benchmark the actual prompt and response sizes and transcription audio. Resource sizing should use concurrent sessions, time-to-first-token, tokens per second, model context size, transcription latency, and memory/GPU utilization from representative loads. No specific GPU or instance size is assumed by this prototype. A local LLM service must expose the OpenAI-compatible chat-completions endpoint; a local transcription service must provide an equivalent in-memory transcription API. Both must keep prompts, audio, and logs inside the approved environment and have an operational owner for monitoring, upgrades, and capacity.

The demo still needs provider credentials/configuration, deployment of migration `20261017000000_mock_interview_sessions.sql`, and an operational check that the hourly cleanup task is running. Before production, add per-candidate rate limits and concurrency caps for question generation and final reviews. French advice sheets download as a server-generated PDF. Arabic and Derja use the browser's print dialog so the installed Arabic font and text shaping can produce a readable PDF; test this on the demo browsers before presenting it as production-ready.

## Goal

Add a candidate practice experience that runs a realistic, role-focused mock interview and gives useful feedback on answer quality, topic understanding, and speaking confidence. Candidates can answer by typing, audio, or (as an optional later mode) video. This is a coaching feature, not a hiring assessment.

## Existing building blocks

- The product already has a React/Vite frontend in `front/` and a FastAPI backend in `back/`.
- Candidate routes and navigation are assembled in `front/src/App.tsx`.
- `back/app/features/employee/routers/assistant.py` provides authenticated assistant and audio transcription endpoints.
- `back/app/features/employee/services/voice.py` transcribes supported audio formats with Groq Whisper; recordings are currently held in memory.
- `back/shared_llm/client.py` supplies the configured OpenAI-compatible chat completion client.
- Candidate profile, skills, occupations, and job matches can provide context for personalized questions.

## First-release behavior

1. Candidate-only **Mock interview** page, reachable from candidate navigation. The candidate chooses an occupation, custom title, or applied offer, plus length and language.
2. The candidate reviews a data-use disclosure and explicitly consents before sending any selected title, applied offer context, and answers for question generation and coaching.
3. The app asks one question at a time, with an optional contextual follow-up and a structuring tip.
4. Typed responses and in-memory browser audio transcription are supported. Candidates can inspect and edit the transcript before submitting it.
5. The final review gives evidence-based encouragement, concrete next steps, and example phrasing per answer, with no score or verdict.

## Feedback model

- **Understanding:** Evaluate whether the answer addresses the question, explains relevant concepts accurately, and gives a concrete example when appropriate. Ground feedback in the question, answer, and relevant role requirements. Include evidence and a plain-language explanation so candidates can see why feedback was given.
- **Answer quality:** Review relevance, specificity, structure (for example, situation/action/result), and completeness. Suggest one concrete improvement per answer.
- **Confidence:** Treat confidence as a coaching signal, not a fact inferred from personality, face, accent, or demographic traits. In the first release, use optional candidate self-ratings plus observable delivery measures from audio such as pace, long pauses, and filler-word frequency. Explain these signals, allow the candidate to skip them, and avoid diagnosing emotion or assigning an authoritative confidence label.
- **Video:** Defer video analysis until a later, separately consented phase. If video capture is offered, use it only for the candidate's own playback unless there is a clear, explicitly opted-in coaching use. Do not infer confidence, honesty, emotion, or competence from facial appearance, eye contact, or body shape.
- **Language:** Start with languages supported by the configured model and transcription service; validate Tunisian Arabic/Derja, Arabic, and French quality before claiming support. Preserve the original transcript and let candidates correct transcription errors.

## Suggested implementation shape

### Backend

- Create an employee feature module for mock interviews with authenticated routes to start a session, submit an answer, and request a final review.
- Keep the first release stateless between requests where practical: the client sends the current interview context and receives the next question or feedback. If persistence is later needed, add explicit session/answer tables with ownership, retention, and deletion rules.
- Use the shared LLM client for question generation and structured feedback; define and validate response schemas so malformed model output cannot break the interview UI.
- Reuse existing candidate profile/job data through backend services. Keep prompts bounded, avoid including unnecessary personal data, and make the AI's feedback non-determinative.
- For audio, reuse transcription infrastructure or extract a shared service. Enforce size/type/duration limits, process in memory, and return transcript text only. Do not send video to a model in the first release.
- Add rate limits, provider timeout/error handling, and a clear fallback when the LLM or transcription provider is unavailable.

### Frontend

- Add a candidate page and route, interview setup, one-question-at-a-time interaction, audio recording/transcript correction, progress indicator, and end-of-session review.
- Make keyboard access, mobile layouts, recording state, permission denial, retry, and transcript correction part of the initial interaction design.
- Keep feedback understandable: separate answer understanding from delivery coaching, show the evidence behind feedback, and let candidates retry a question.

### Privacy and responsible use

- Require an explicit choice before microphone use; explain what is sent to configured AI/transcription providers.
- Do not persist recordings in the initial release. If answer/session history is saved later, disclose retention, provide deletion, and scope access to the candidate.
- Never expose mock interview scores or transcripts to employers or use them in matching, ranking, hiring, or ministry analytics.
- Label generated feedback as approximate, provide a way to flag unhelpful feedback, and avoid unsupported claims about confidence or understanding.

## Delivery phases

1. **Prototype:** typed, stateless interview for a selected occupation; tailored questions and structured understanding/answer-quality feedback.
2. **Audio mode:** browser recording, in-memory transcription, editable transcript, and opt-in delivery coaching based on transparent speech measures.
3. **Evaluation and hardening:** test representative occupations, answer quality, language/transcription failure cases, malformed model outputs, privacy behavior, and accessibility; tune prompts and guardrails from observed results.
4. **Optional video exploration:** only after user research and privacy review establish a clear candidate benefit. Begin with candidate-controlled recording/playback; do not add face-based confidence inference.

## Decisions to make before implementation

- Should the experience be strictly ephemeral, or should candidates be able to save and revisit feedback?
- Which languages should be supported at launch, and which model/provider is available in the deployment environment?
- Should the MVP include only typed answers, or typed plus audio from the start?
- What interview lengths and question categories best fit the candidate audience?

## Acceptance criteria for the first release

- An authenticated candidate can start an occupation-focused interview, answer multiple questions, and receive a final review.
- Feedback distinguishes answer understanding from answer structure and gives specific evidence and next steps.
- Candidates can decline audio and use text; if audio is enabled, they can inspect and correct the transcript before it is evaluated.
- Provider failures and unsupported/empty transcripts produce recoverable messages.
- No raw audio, video, or interview history is persisted by default, and mock interview results are not made available to employers.
- The UI clearly describes the limits of AI-generated coaching and does not claim to objectively measure confidence.
