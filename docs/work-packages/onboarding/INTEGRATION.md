# Onboarding migration notes

Voice onboarding, guided questions, transcription, and offer-text generation run inside the shared API and store reviewed answers in the shared database.

The former recap-audio playback feature is intentionally incomplete. It requires retaining each raw answer recording so recordings can be assembled later. The consolidated endpoint currently holds each recording only while transcribing it, then discards it; the existing onboarding tests enforce that data-minimization behavior. No audio recap endpoint is registered. Confirm a retention policy before restoring recap playback.
