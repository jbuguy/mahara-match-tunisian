"""Static reference data shared by the ORM, the JSON contracts and the SQL seed."""

# The 24 Tunisian governorates, keyed by ISO 3166-2:TN code.
GOVERNORATES: dict[str, tuple[str, str]] = {
    "TN-11": ("Tunis", "تونس"),
    "TN-12": ("Ariana", "أريانة"),
    "TN-13": ("Ben Arous", "بن عروس"),
    "TN-14": ("Manouba", "منوبة"),
    "TN-21": ("Nabeul", "نابل"),
    "TN-22": ("Zaghouan", "زغوان"),
    "TN-23": ("Bizerte", "بنزرت"),
    "TN-31": ("Béja", "باجة"),
    "TN-32": ("Jendouba", "جندوبة"),
    "TN-33": ("Le Kef", "الكاف"),
    "TN-34": ("Siliana", "سليانة"),
    "TN-41": ("Kairouan", "القيروان"),
    "TN-42": ("Kasserine", "القصرين"),
    "TN-43": ("Sidi Bouzid", "سيدي بوزيد"),
    "TN-51": ("Sousse", "سوسة"),
    "TN-52": ("Monastir", "المنستير"),
    "TN-53": ("Mahdia", "المهدية"),
    "TN-61": ("Sfax", "صفاقس"),
    "TN-71": ("Gafsa", "قفصة"),
    "TN-72": ("Tozeur", "توزر"),
    "TN-73": ("Kébili", "قبلي"),
    "TN-81": ("Gabès", "قابس"),
    "TN-82": ("Médenine", "مدنين"),
    "TN-83": ("Tataouine", "تطاوين"),
}

# Proficiency scale used by candidate_skills.level, job_offer_skills.min_level,
# skill_gaps and training_course_skills.target_level.
PROFICIENCY_LEVELS: dict[int, str] = {
    1: "beginner",
    2: "intermediate",
    3: "advanced",
    4: "expert",
}

# Dimension of every vector stored in public.embeddings. Changing it requires a
# migration and a full re-embedding.
EMBEDDING_DIM = 768

# Matching weights from the WP3 specification (sum = 1.0).
DEFAULT_SCORING_WEIGHTS: dict[str, float] = {
    "hard_skills": 0.50,
    "experience": 0.20,
    "soft_skills": 0.15,
    "location": 0.15,
}
