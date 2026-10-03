"""Dev-only reference data: ~45 skills (SK-9001...) and ~12 occupations (OC-9001...).

Run from backend/:  python -m scripts.seed_dev
Only runs when APP_ENV is dev/development. Safe to run again: rows are upserted by code.
The 9xxx codes never collide with the team's real list.
"""

import sys

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_engine
from app.models import Occupation, Skill

DEV_ENVS = {"dev", "development"}

# (code, label_fr, skill_type, alt_labels). alt_labels hold accent-free spellings and synonyms for search.
SKILLS = [
    ("SK-9001", "Vente", "hard", ["vendeur", "vendeuse", "vente en magasin", "commerce"]),
    ("SK-9002", "Service client", "hard", ["relation client", "accueil client", "centre d'appels"]),
    ("SK-9003", "Logistique", "hard", ["gestion de stock", "magasinier", "entrepot"]),
    ("SK-9004", "Conduite de véhicule léger (permis B)", "hard", ["conduite", "chauffeur", "permis b", "vehicule"]),
    ("SK-9005", "Conduite poids lourd (permis C)", "hard", ["camion", "poids lourd", "permis c"]),
    ("SK-9006", "Soudure", "hard", ["soudeur", "soudage", "soudure a l'arc"]),
    ("SK-9007", "Cuisine", "hard", ["cuisinier", "cuisiniere", "restauration"]),
    ("SK-9008", "Pâtisserie", "hard", ["patisserie", "patissier", "boulangerie"]),
    ("SK-9009", "Excel", "hard", ["microsoft excel", "tableur", "tableaux"]),
    ("SK-9010", "Bureautique (Word, e-mail)", "hard", ["bureautique", "word", "informatique de base"]),
    ("SK-9011", "Développement web", "hard", ["developpement web", "html", "css", "javascript", "site web"]),
    ("SK-9012", "Comptabilité", "hard", ["comptabilite", "comptable", "facturation"]),
    ("SK-9013", "Secrétariat", "hard", ["secretariat", "assistant administratif", "accueil"]),
    ("SK-9014", "Électricité du bâtiment", "hard", ["electricite", "electricien", "batiment"]),
    ("SK-9015", "Plomberie", "hard", ["plombier", "sanitaire"]),
    ("SK-9016", "Maçonnerie", "hard", ["maconnerie", "macon", "chantier"]),
    ("SK-9017", "Mécanique automobile", "hard", ["mecanique", "mecanicien", "garage"]),
    ("SK-9018", "Couture", "hard", ["couturier", "couturiere", "confection", "textile"]),
    ("SK-9019", "Caisse", "hard", ["caissier", "caissiere", "encaissement"]),
    ("SK-9020", "Travaux agricoles", "hard", ["agriculture", "ouvrier agricole", "recolte"]),
    ("SK-9021", "Nettoyage", "hard", ["agent d'entretien", "menage", "proprete"]),
    ("SK-9022", "Service en salle", "hard", ["serveur", "serveuse", "cafe", "restaurant"]),
    ("SK-9023", "Travail en équipe", "soft", ["travail en equipe", "esprit d'equipe"]),
    ("SK-9024", "Communication", "soft", ["communiquer", "expression orale"]),
    ("SK-9025", "Ponctualité", "soft", ["ponctualite", "assiduite"]),
    ("SK-9026", "Résolution de problèmes", "soft", ["resolution de problemes", "debrouillard"]),
    ("SK-9027", "Organisation", "soft", ["organise", "rigueur"]),
    ("SK-9028", "Arabe", "language", ["arabe", "arabic", "derja"]),
    ("SK-9029", "Français", "language", ["francais", "french"]),
    ("SK-9030", "Anglais", "language", ["anglais", "english"]),
    ("SK-9031", "Allemand", "language", ["allemand", "german", "deutsch"]),
    ("SK-9032", "Italien", "language", ["italien", "italian"]),
    # Tech skills (added with CV import, so developer CVs match too)
    ("SK-9033", "JavaScript", "hard", ["javascript", "ecmascript"]),
    ("SK-9034", "TypeScript", "hard", ["typescript"]),
    ("SK-9035", "Python", "hard", ["python", "django", "flask"]),
    ("SK-9036", "Java", "hard", ["java", "jee", "j2ee"]),
    ("SK-9037", "PHP", "hard", ["php", "laravel", "symfony"]),
    ("SK-9038", "React", "hard", ["react", "react js", "reactjs"]),
    ("SK-9039", "Node.js", "hard", ["node js", "nodejs", "express js", "expressjs"]),
    ("SK-9040", "Spring Boot", "hard", ["spring boot", "spring"]),
    ("SK-9041", "Bases de données SQL", "hard", ["sql", "mysql", "postgresql", "sqlite", "oracle", "base de donnees"]),
    ("SK-9042", "MongoDB", "hard", ["mongodb", "mongo", "nosql"]),
    ("SK-9043", "Git", "hard", ["git", "github", "gitlab"]),
    ("SK-9044", "API REST", "hard", ["api rest", "rest api", "restful"]),
    ("SK-9045", "Développement mobile", "hard", ["developpement mobile", "android", "flutter", "react native", "kotlin"]),
    ("SK-9046", "Intelligence artificielle", "hard", ["intelligence artificielle", "machine learning", "deep learning"]),
]

OCCUPATIONS = [
    ("OC-9001", "Vendeur / Vendeuse en magasin"),
    ("OC-9002", "Conseiller / Conseillère clientèle"),
    ("OC-9003", "Magasinier / Magasinière"),
    ("OC-9004", "Chauffeur-livreur / Chauffeuse-livreuse"),
    ("OC-9005", "Soudeur / Soudeuse"),
    ("OC-9006", "Cuisinier / Cuisinière"),
    ("OC-9007", "Assistant / Assistante administratif"),
    ("OC-9008", "Développeur / Développeuse web"),
    ("OC-9009", "Électricien / Électricienne du bâtiment"),
    ("OC-9010", "Serveur / Serveuse"),
    ("OC-9011", "Comptable"),
    ("OC-9012", "Couturier / Couturière"),
]


def seed(db: Session) -> None:
    skills = insert(Skill).values([
        {"code": code, "label_fr": label, "skill_type": skill_type, "alt_labels": alt, "status": "validated"}
        for code, label, skill_type, alt in SKILLS
    ])
    db.execute(skills.on_conflict_do_update(
        index_elements=[Skill.code],
        set_={
            "label_fr": skills.excluded.label_fr,
            "skill_type": skills.excluded.skill_type,
            "alt_labels": skills.excluded.alt_labels,
            "status": skills.excluded.status,
        },
    ))
    occupations = insert(Occupation).values([{"code": code, "title_fr": title} for code, title in OCCUPATIONS])
    db.execute(occupations.on_conflict_do_update(
        index_elements=[Occupation.code],
        set_={"title_fr": occupations.excluded.title_fr},
    ))
    db.commit()


def main() -> int:
    app_env = get_settings().app_env.strip().lower()
    if app_env not in DEV_ENVS:
        print(f"Refusing to seed: APP_ENV is '{app_env}', expected dev or development.", file=sys.stderr)
        return 1
    with Session(get_engine()) as db:
        seed(db)
    print(f"Seeded {len(SKILLS)} skills (SK-9001...) and {len(OCCUPATIONS)} occupations (OC-9001...).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
