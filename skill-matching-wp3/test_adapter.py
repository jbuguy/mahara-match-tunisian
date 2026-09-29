from cv_parser import build_profile_from_cv
from cv_adapter import adapter_profil_vers_contrat
from mahara_data.schemas.profile import CandidateProfile
import json

brut = build_profile_from_cv("data/cv_exemple.docx", "cand_demo")
adapte = adapter_profil_vers_contrat(brut, governorate_code="TN-71")

print(json.dumps(adapte, indent=2, ensure_ascii=False))

profil = CandidateProfile(**adapte)   # échoue si le format est faux
print("Format valide selon le contrat WP1")