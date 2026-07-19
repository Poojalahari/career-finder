import json
import re
from pathlib import Path


ALIASES = {
    "js": "javascript",
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "postgres": "postgresql",
    "node": "node.js",
    "ui": "ui/ux",
    "ux": "ui/ux",
}


def _normalize(text):
    text = (text or "").lower()
    for alias, canonical in ALIASES.items():
        text = re.sub(rf"\b{re.escape(alias)}\b", canonical, text)
    return text


def _terms(text):
    return set(re.findall(r"[a-z0-9+#./]+(?:\s+[a-z0-9+#./]+)?", _normalize(text)))


def _contains(term, terms, raw):
    return term in terms or term in raw


def load_taxonomy():
    path = Path(__file__).with_name("career_taxonomy.json")
    return json.loads(path.read_text(encoding="utf-8"))


def recommend_careers(skills, interests, cgpa, certifications):
    skill_terms = _terms(skills)
    interest_terms = _terms(interests)
    cert_terms = _terms(certifications)
    raw = _normalize(f"{skills} {interests} {certifications}")
    results = []
    for career in load_taxonomy():
        matched_skills = [s for s in career["skills"] if _contains(s, skill_terms, raw)]
        matched_interests = [i for i in career["interests"] if _contains(i, interest_terms, raw)]
        matched_certs = [c for c in career["certifications"] if _contains(c, cert_terms, raw)]
        skill_score = len(matched_skills) / max(len(career["skills"]), 1) * 50
        interest_score = len(matched_interests) / max(len(career["interests"]), 1) * 25
        cert_score = len(matched_certs) / max(len(career["certifications"]), 1) * 15
        cgpa_score = min(max(float(cgpa), 0), 10) / 10 * 10
        total = round(skill_score + interest_score + cert_score + cgpa_score)
        missing = [s for s in career["skills"] if s not in matched_skills][:5]
        results.append(
            {
                **career,
                "match_percentage": min(total, 100),
                "matched_skills": matched_skills,
                "missing_skills": missing,
                "recommended_certifications": career["certifications"],
                "salary_disclaimer": "Salary varies by location, company, experience, and market conditions.",
                "explanation": (
                    f"Matched {len(matched_skills)} core skills, {len(matched_interests)} interests, "
                    f"{len(matched_certs)} certifications, plus CGPA contribution."
                ),
            }
        )
    ranked = sorted(results, key=lambda item: item["match_percentage"], reverse=True)
    if ranked[0]["match_percentage"] <= 10:
        ranked[0]["explanation"] = "Your inputs were broad, so this is a starting point. Add more specific skills for a stronger match."
    return {"top": ranked[0], "alternatives": ranked[1:4]}
