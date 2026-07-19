import re
from collections import Counter


ALIASES = {
    "js": "javascript",
    "node": "node.js",
    "postgres": "postgresql",
    "ml": "machine learning",
    "ai": "artificial intelligence",
}
STOP_WORDS = {
    "and", "or", "the", "with", "for", "from", "this", "that", "your", "you", "are", "will",
    "have", "has", "our", "can", "a", "an", "to", "of", "in", "on", "as", "by", "is",
}
ACTION_VERBS = {"built", "created", "led", "improved", "reduced", "designed", "implemented", "automated", "launched"}


def normalize_keyword(value: str) -> str:
    value = value.lower().strip(" .,:;()[]{}")
    return ALIASES.get(value, value)


def tokens(text):
    raw = re.findall(r"[a-zA-Z][a-zA-Z0-9+#.]{1,}", (text or "").lower())
    return [normalize_keyword(t) for t in raw if t not in STOP_WORDS]


def important_keywords(text, limit=30):
    counts = Counter(tokens(text))
    return [word for word, _ in counts.most_common(limit)]


def detect_sections(text):
    lower = text.lower()
    return {
        "contact": bool(re.search(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", lower)) and bool(re.search(r"(\+?\d[\d\s().-]{8,})", lower)),
        "summary": any(x in lower for x in ["summary", "profile", "objective"]),
        "skills": "skills" in lower or "technical skills" in lower,
        "experience": any(x in lower for x in ["experience", "employment", "work history"]),
        "education": "education" in lower or "university" in lower or "college" in lower,
        "projects": "project" in lower,
        "certifications": "certification" in lower or "certified" in lower,
    }


def analyze_resume(text, job_description=""):
    resume_keywords = set(important_keywords(text, 80))
    jd_keywords = set(important_keywords(job_description, 40))
    matched = sorted(resume_keywords & jd_keywords)
    missing = sorted(jd_keywords - resume_keywords)
    sections = detect_sections(text)
    quantified = len(re.findall(r"(\d+%|\$\d+|\b\d+\s*(users|clients|projects|hours|days|months)\b)", text.lower()))
    action_count = sum(1 for t in tokens(text) if t in ACTION_VERBS)
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if len(p.split()) > 80]
    stuffing = [word for word, count in Counter(tokens(text)).items() if count >= 15 and word not in STOP_WORDS]
    return {
        "sections": sections,
        "resume_keywords": sorted(resume_keywords)[:50],
        "job_keywords": sorted(jd_keywords),
        "matched_keywords": matched[:30],
        "missing_keywords": missing[:30],
        "skill_match_percentage": round(len(matched) / max(len(jd_keywords), 1) * 100) if jd_keywords else 0,
        "quantified_achievement_count": quantified,
        "action_verb_count": action_count,
        "warnings": {
            "long_paragraphs": len(paragraphs),
            "keyword_stuffing": stuffing[:10],
            "table_or_columns_risk": bool(re.search(r" {6,}\S", text)),
        },
        "contact": {
            "email": bool(re.search(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", text.lower())),
            "phone": bool(re.search(r"(\+?\d[\d\s().-]{8,})", text)),
            "links": bool(re.search(r"(linkedin\.com|github\.com|https?://)", text.lower())),
        },
    }
