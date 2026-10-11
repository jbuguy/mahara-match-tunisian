"""CV import: read a PDF or DOCX and turn it into a draft for the profile form.

Best effort only: the candidate checks everything in the form before saving, and nothing here touches the
database except reading the skills catalog. Text is compared lower-case and without accents ("fold").
"""

import io
import re
import unicodedata
from dataclasses import dataclass

import docx
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Skill
from ..schemas import CvDraft, CvEducation, CvExperience, CvImportOut, CvSkill

MAX_CV_BYTES = 5 * 1024 * 1024
MAX_PDF_PAGES = 10  # a CV is 1-3 pages; this keeps a huge PDF from tying up the server
MIN_TEXT_CHARS = 20  # less than this is a scanned CV (images only)
UNREADABLE = "Nous n'avons pas pu lire ce CV, remplissez le formulaire"

PDF_START = b"%PDF-"
ZIP_START = b"PK\x03\x04"  # a .docx is a zip file


class UnreadableCv(Exception):
    """The file couldn't be opened, or it has no text (a scanned CV)."""


# ---------------------------------------------------------------------------
# Reading the file
# ---------------------------------------------------------------------------

def file_kind(filename: str, data: bytes) -> str | None:
    """'pdf' or 'docx' when both the extension and the first bytes agree, else None."""
    name = filename.lower()
    if name.endswith(".pdf") and data.startswith(PDF_START):
        return "pdf"
    if name.endswith(".docx") and data.startswith(ZIP_START):
        return "docx"
    return None


def read_text(kind: str, data: bytes) -> str:
    try:
        text = _pdf_text(data) if kind == "pdf" else _docx_text(data)
    except Exception as exc:  # broken or password-protected files: pypdf and python-docx raise many kinds
        raise UnreadableCv from exc
    if len(re.sub(r"\s", "", text)) < MIN_TEXT_CHARS:
        raise UnreadableCv
    return text


# Kerning after a capital with an overhang makes pypdf see a space: "T echnologies", "T ailwind".
KERNING_SPLIT = re.compile(r"\b([FPTVWY]) (?=[a-zà-ÿ]{2})")


def _pdf_text(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    text = "\n".join(page.extract_text() or "" for page in reader.pages[:MAX_PDF_PAGES])
    return KERNING_SPLIT.sub(r"\1", text)


def _docx_text(data: bytes) -> str:
    document = docx.Document(io.BytesIO(data))
    lines = []
    # Word CV templates often put the name and contact details in the page header.
    for section in document.sections:
        lines += [paragraph.text for paragraph in section.header.paragraphs]
    for block in document.iter_inner_content():  # paragraphs and tables, in reading order
        if isinstance(block, docx.table.Table):
            for row in block.rows:
                cells = []
                for cell in row.cells:  # a merged cell comes back once per column it spans
                    if not cells or cell.text != cells[-1]:
                        cells.append(cell.text)
                lines += cells
        else:
            lines.append(block.text)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def fold(text: str) -> str:
    """Lower-case without accents, one character for one (so positions match the original text)."""
    return "".join(unicodedata.normalize("NFD", char.lower())[0] for char in text.replace("’", "'"))


def words(text: str) -> str:
    """Folded words separated by single spaces, with a space at both ends: ready for ' term ' in ..."""
    return " " + " ".join(re.findall(r"[a-z0-9]+", fold(text))) + " "


BULLET = re.compile(r"^\s*[-•*▪◦·–—>]\s*")
# Title and employer: "Vendeur - Monoprix", "Vendeur, Monoprix", "Vendeur chez Monoprix" ("Chauffeur-livreur" stays whole).
PARTS = re.compile(r"\s+[-–—|@]\s+|\s*,\s*|\s+chez\s+|\s*\|\s*", re.IGNORECASE)
TRIM = " \t-–—|,;:()[]"
LINE_LABEL = re.compile(r"^[^:,;]{1,50}:\s*(?=\S)")  # "Technologies:" or "Université :" in front of the content


def _clip(text: str, limit: int) -> str:
    return text.strip(TRIM)[:limit].strip()


# ---------------------------------------------------------------------------
# Sections: the CV's headings ("Expérience", "Formation"...)
# ---------------------------------------------------------------------------

HEADINGS = {
    "experience": ("experience", "parcours professionnel", "emploi", "historique professionnel", "stage"),
    "education": ("formation", "education", "diplome", "etudes", "cursus", "parcours scolaire",
                  "parcours academique", "scolarite"),
    "skills": ("competence", "savoir-faire", "savoir faire", "aptitude", "skills", "connaissances"),
    "languages": ("langue",),
    "other": ("centre", "loisir", "interet", "projet", "certificat", "reference", "profil", "a propos",
              "contact", "information", "coordonnee", "objectif", "qualite", "activite", "divers", "permis"),
}


def _heading(line: str) -> tuple[str, str] | None:
    """(section, text after 'Heading :') when the line is a heading: short, no digits, starts with a known word."""
    title, _, after = line.partition(":")
    folded = fold(title).strip(" \t•*-:").strip()
    if not folded or re.search(r"\d", folded) or len(folded.split()) > 5:
        return None
    for section, starts in HEADINGS.items():
        if folded.startswith(starts):
            return section, after.strip()
    return None


def split_sections(lines: list[str]) -> dict[str, list[str]]:
    """Lines by section; lines before the first heading go to 'top'."""
    sections: dict[str, list[str]] = {"top": []}
    current = "top"
    for line in lines:
        found = _heading(line)
        if found:
            current, after = found
            sections.setdefault(current, [])
            if after:  # "Compétences : Vente, Excel"
                sections[current].append(after)
        else:
            sections[current].append(line)
    return sections


# ---------------------------------------------------------------------------
# Name, email, phone
# ---------------------------------------------------------------------------

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# 8 digits starting 2-9 (one space, dot or dash allowed between digits), optionally after +216 / 00216.
PHONE = re.compile(r"(?<![\d+])(?P<prefix>(?:\+|00)216[\s.-]?)?(?P<number>[2-9](?:[\s.-]?\d){7})(?!\d)")
YEAR_RANGE = re.compile(r"(19|20)\d\d(19|20)\d\d")  # "2019-2020" looks like a phone number too
NOT_A_NAME = re.compile(r"^(cv|c\.v\.?|curriculum vitae|resume)$")


def find_name(lines: list[str]) -> str:
    """The first line that looks like a name (skipping 'Curriculum vitae', contact lines...)."""
    for line in lines[:5]:
        line = line.strip()
        if NOT_A_NAME.match(fold(line)) or re.search(r"[\d@:]", line) or _heading(line):
            continue
        if len(line.split()) > 5 or len(line) > 60:
            return ""
        return line.title() if line.isupper() else line
    return ""


def find_email(text: str) -> str:
    match = EMAIL.search(text)
    return match.group(0).lower() if match else ""


def find_phone(text: str) -> str:
    for match in PHONE.finditer(text):
        digits = re.sub(r"\D", "", match.group("number"))
        if YEAR_RANGE.fullmatch(digits):
            continue
        number = f"{digits[:2]} {digits[2:5]} {digits[5:]}"
        return f"+216 {number}" if match.group("prefix") else number
    return ""


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------

@dataclass
class CatalogSkill:
    code: str
    label_fr: str
    terms: list[str]  # label and alternative labels, as ' folded words '


def load_skills(db: Session) -> list[CatalogSkill]:
    """The validated skills catalog, in one query."""
    rows = db.execute(select(Skill.code, Skill.label_fr, Skill.alt_labels).where(Skill.status == "validated"))
    skills = []
    for code, label_fr, alt_labels in rows:
        terms = {words(term) for term in [label_fr, *(alt_labels or [])] if isinstance(term, str)}
        skills.append(CatalogSkill(code, label_fr, [term for term in terms if len(term.strip()) >= 2]))
    return skills


def find_skills(text: str, catalog: list[CatalogSkill]) -> list[CvSkill]:
    """Catalog skills named anywhere in the CV, in the order they first appear."""
    folded = words(text)
    found = []
    for skill in catalog:
        positions = [folded.find(term) for term in skill.terms if term in folded]
        if positions:
            found.append((min(positions), skill))
    found.sort(key=lambda item: item[0])
    return [CvSkill(code=skill.code, label_fr=skill.label_fr) for _, skill in found]


def unmatched_words(lines: list[str], catalog: list[CatalogSkill]) -> list[str]:
    """Items of the Compétences / Langues sections that match no catalog skill, e.g. ['Photoshop']."""
    items = []
    for line in lines:
        line = LINE_LABEL.sub("", BULLET.sub("", line))  # "Langages: Java, Python" → "Java, Python"
        for item in re.split(r"[,;•·|/]|\s+-\s+", line):
            item = _clip(re.sub(r"\(.*?\)", "", item), 60)
            if len(item) < 2 or item in items:
                continue
            padded = words(item)
            if padded.strip() and not any(term in padded for skill in catalog for term in skill.terms):
                items.append(item)
    return items[:30]


# ---------------------------------------------------------------------------
# Education
# ---------------------------------------------------------------------------

# Most advanced first: a line naming two levels ("Master, après une licence") gets the higher one.
DIPLOMAS = [
    ("doctorate", r"\bdoctorat\b|\bphd\b"),
    ("engineer", r"\bingenieur\b"),
    ("master", r"\bmasters?\b|\bmastere\b"),
    ("licence", r"\blicence\b"),
    ("vocational_bts", r"\bbts\b|\btechnicien superieur\b"),
    ("baccalaureate", r"\bbaccalaureat\b|\bbac\b(?!\s*\+)"),
    ("vocational_btp", r"\bbtp\b|\bbrevet de technicien professionnel\b"),
    ("vocational_cap", r"\bcap\b|\bcertificat d'aptitude professionnelle\b"),
]
LEVEL_RANK = {level: rank for rank, (level, _) in enumerate(reversed(DIPLOMAS))}
SCHOOL = re.compile(r"universit|institut|\biset\b|\bisg\b|\benit\b|ecole|faculte|lycee|centre|\bcollege\b")
YEAR = re.compile(r"(?<!\d)(19[5-9]\d|20\d\d)(?!\d)")


def parse_education(line: str) -> CvEducation | None:
    """'Licence en gestion, ISG Tunis, 2020' → level licence, field 'Gestion', institution 'ISG Tunis', 2020."""
    folded = fold(line)
    for level, pattern in DIPLOMAS:
        diploma = re.search(pattern, folded)
        if diploma:
            break
    else:
        return None
    years = [int(year) for year in YEAR.findall(folded)]
    no_years = YEAR.sub("", line)
    parts = [part for part in PARTS.split(BULLET.sub("", no_years)) if part.strip(TRIM)]
    institution = next((part for part in parts[1:] if SCHOOL.search(fold(part))), None)
    first = parts[0] if parts else ""
    found = re.search(pattern, fold(first))
    after_diploma = found.end() if found else 0
    # The school on the same line, without a separator: "Licence en génie logiciel Université: Faculté de Bizerte".
    school = SCHOOL.search(fold(first), after_diploma)
    if school and institution is None:
        first, institution = first[:school.start()], first[school.start():]
    # The field of study is what follows the diploma's name: "Licence en gestion" → "gestion".
    field = re.sub(r"^[\s:]*(?:(?:en|de|du|des)\s+|d')", "", first[after_diploma:], flags=re.IGNORECASE)
    field = _clip(re.sub(r"\s+(?:avec\s+)?mention\b.*$", "", field, flags=re.IGNORECASE), 200)
    institution = _clip(LINE_LABEL.sub("", institution), 200) if institution else ""
    return CvEducation(
        level=level,
        field_of_study=(field[0].upper() + field[1:]) if field else None,
        institution=institution or None,
        graduation_year=max(years) if years else None,  # "2021 - 2024": the diploma is from 2024
    )


def parse_educations(lines: list[str]) -> list[CvEducation]:
    """One entry per diploma; a next line about the same diploma ('Baccalauréat en Mathématiques') completes it."""
    educations: list[CvEducation] = []
    for line in lines:
        education = parse_education(line)
        if education is None:
            continue
        previous = educations[-1] if educations else None
        if previous and previous.level == education.level and education.graduation_year in (
            None, previous.graduation_year,
        ):
            for name in ("field_of_study", "institution", "graduation_year"):
                if getattr(previous, name) is None:
                    setattr(previous, name, getattr(education, name))
            continue
        educations.append(education)
    return educations[:20]


# ---------------------------------------------------------------------------
# Experience
# ---------------------------------------------------------------------------

MONTHS = {
    "janv": 1, "janvier": 1, "fev": 2, "fevr": 2, "fevrier": 2, "mars": 3, "avr": 4, "avril": 4, "mai": 5,
    "juin": 6, "juil": 7, "juillet": 7, "aout": 8, "sept": 9, "septembre": 9, "oct": 10, "octobre": 10,
    "nov": 11, "novembre": 11, "dec": 12, "decembre": 12,
}
# "2019", "03/2019", "15/03/2019", "mars 2019" (on folded text)
DATE = re.compile(
    r"(?<![\d/])(?:(?P<name>" + "|".join(sorted(MONTHS, key=len, reverse=True)) + r")\.?\s+"
    r"|(?:\d{1,2}[/.-])?(?P<month>0?[1-9]|1[0-2])[/.-])?(?P<year>(?:19|20)\d\d)(?!\d)"
)
ONGOING = re.compile(r"aujourd'hui|a ce jour|ce jour|present|actuel(?:lement)?|en cours|maintenant")
BETWEEN_DATES = re.compile(r"\s*(?:-|–|—|a|au|jusqu'a|jusqu'au|/)?\s*")


def _iso(match: re.Match, default_month: int) -> str:
    month = MONTHS[match.group("name")] if match.group("name") else int(match.group("month") or default_month)
    return f"{match.group('year')}-{month:02d}-01"


def find_dates(line: str) -> tuple[str, str, str]:
    """(start_date, end_date, the line without them); dates are 'YYYY-MM-01' or ''. End '' = ongoing or unknown."""
    folded = fold(line)
    start = DATE.search(folded)
    if not start:
        return "", "", line
    start_date, end_date, span_end = _iso(start, 1), "", start.end()
    end = DATE.search(folded, start.end()) or ONGOING.search(folded, start.end())
    if end and BETWEEN_DATES.fullmatch(folded[start.end():end.start()]):
        span_end = end.end()
        if end.re is DATE:
            end_date = _iso(end, 12)  # "2019 - 2020": until the end of 2020
    if end_date and end_date < start_date:
        end_date = ""
    span_start = start.start()
    before = re.search(r"(?:depuis|de|du)\s*$", folded[:span_start])
    if before:
        span_start = before.start()
    rest = line[:span_start] + line[span_end:]
    return start_date, end_date, re.sub(r"\(\s*\)|\[\s*\]", "", rest)


# A company written in capitals at the end of the job line: "Développeur full-stack ONRTECH".
CAPS_EMPLOYER = re.compile(r"^(?P<title>.*\S)\s+(?P<employer>[A-Z][A-Z0-9&.'-]{3,}(?:\s+[A-Z][A-Z0-9&.'-]+)*)$")
INTERNSHIP = re.compile(r"^stage\s*:\s*", re.IGNORECASE)


def _is_sentence(text: str) -> bool:
    """Descriptions are sentences; job lines are short ('Vendeur - Monoprix')."""
    return text[:1].islower() or len(text.split()) > 8 or text.endswith(".")


def _title_and_employer(text: str) -> tuple[str, str]:
    title, employer = (PARTS.split(text, maxsplit=1) + [""])[:2]
    if not employer and (caps := CAPS_EMPLOYER.match(title)):
        title, employer = caps.group("title"), caps.group("employer")
    if INTERNSHIP.match(title):  # "Stage : Développeur" → "Développeur (stage)"
        return f"{_clip(INTERNSHIP.sub('', title), 190)} (stage)", _clip(employer, 200)
    return _clip(title, 200), _clip(employer, 200)


def parse_experiences(lines: list[str]) -> list[CvExperience]:
    """Each line under 'Expérience' is a job ('Poste - Employeur  2019-2021'); bullet points and sentences
    below it describe it."""
    jobs: list[CvExperience] = []
    waiting_dates: tuple[str, str] | None = None  # a line with only dates, before its job
    for line in lines:
        if not line.strip():
            continue
        start_date, end_date, rest = find_dates(line)
        rest = rest.strip(TRIM)
        if jobs and (BULLET.match(line) or (not start_date and _is_sentence(rest))):
            description = "\n".join(filter(None, [jobs[-1].description, BULLET.sub("", line).strip()]))
            jobs[-1].description = description[:2000]
            continue
        if not rest:
            if jobs and not jobs[-1].start_date:
                jobs[-1].start_date, jobs[-1].end_date = start_date, end_date
            elif start_date:
                waiting_dates = (start_date, end_date)
            continue
        if not start_date and waiting_dates:
            start_date, end_date = waiting_dates
        waiting_dates = None
        title, employer = _title_and_employer(rest)
        jobs.append(CvExperience(
            job_title_raw=title,
            employer_name=employer,
            start_date=start_date,
            end_date=end_date,
        ))
    return [job for job in jobs if job.job_title_raw][:50]


# ---------------------------------------------------------------------------
# The draft
# ---------------------------------------------------------------------------

def build_draft(text: str, catalog: list[CatalogSkill]) -> CvImportOut:
    lines = [line.strip() for line in text.splitlines()]
    content = [line for line in lines if line]
    sections = split_sections(content)

    if "education" in sections:
        education_lines = sections["education"]
    else:  # no "Formation" heading: look everywhere except under "Expérience"
        education_lines = [line for name, part in sections.items() if name != "experience" for line in part]
    educations = parse_educations(education_lines)
    best = max((education.level for education in educations), key=LEVEL_RANK.__getitem__, default="")

    return CvImportOut(
        draft=CvDraft(
            full_name=find_name(content),
            email=find_email(text),
            phone=find_phone(text),
            education_level=best,
            skills=find_skills(text, catalog)[:100],
            experiences=parse_experiences(sections.get("experience", [])),
            educations=educations,
        ),
        unmatched_words=unmatched_words(sections.get("skills", []) + sections.get("languages", []), catalog),
    )
