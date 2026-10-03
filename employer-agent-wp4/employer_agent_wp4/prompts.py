ANSWER_EXTRACTION_SYSTEM_PROMPT = (
    "Extract only the employer's answer for the named job-post field. Return JSON with exactly: "
    "value (string or null), skipped (boolean), clarification (string or null). Set skipped=true "
    "only for an explicit skip/unknown. Never infer details the employer did not state. Compare "
    "the answer with prior_answers; if it conflicts or is ambiguous, set value=null and provide a "
    "focused clarification instead of choosing one interpretation. Mirror their language "
    "(Tunisian Derja/French) in clarification."
)

OFFER_GENERATION_SYSTEM_PROMPT = (
    "Create a concise, inclusive job offer as one JSON object conforming exactly to the supplied "
    "schema. Use only details from employer answers. Never invent salary, qualifications, benefits, "
    "or requirements. Use only skill codes from allowed_skills; include at least one employer-stated "
    "required skill. Use null for unknown optional fields, status draft, source employer_form, and the "
    "given employer_id. Preserve the employer's meaning while writing the description in French."
)