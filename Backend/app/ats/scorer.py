from .analyzer import analyze_resume


JD_WEIGHTS = {
    "keyword_match": 35,
    "experience": 20,
    "sections": 15,
    "achievements": 10,
    "education_certs": 8,
    "readability": 7,
    "contact": 5,
}
GENERAL_WEIGHTS = {
    "sections": 25,
    "skills": 20,
    "experience": 20,
    "achievements": 15,
    "readability": 10,
    "education_certs": 5,
    "contact": 5,
}


def score_band(score):
    if score >= 85:
        return "Excellent"
    if score >= 70:
        return "Good"
    if score >= 50:
        return "Needs Improvement"
    return "Weak"


def clamp(value):
    return max(0, min(100, round(value)))


def score_resume(text, page_count, job_description=""):
    analysis = analyze_resume(text, job_description)
    sections = analysis["sections"]
    section_ratio = sum(1 for ok in sections.values() if ok) / len(sections)
    readability = 100
    if analysis["warnings"]["long_paragraphs"]:
        readability -= 20
    if analysis["warnings"]["table_or_columns_risk"]:
        readability -= 15
    if analysis["warnings"]["keyword_stuffing"]:
        readability -= 25
    if page_count > 2:
        readability -= 10
    contact_score = sum(1 for ok in analysis["contact"].values() if ok) / 3 * 100
    achievement_score = min(analysis["quantified_achievement_count"] * 20 + analysis["action_verb_count"] * 5, 100)
    education_cert_score = (50 if sections["education"] else 0) + (50 if sections["certifications"] else 0)
    experience_score = 100 if sections["experience"] else 35

    if job_description:
        keyword_score = analysis["skill_match_percentage"]
        section_scores = {
            "Job-description skill and keyword match": clamp(keyword_score),
            "Relevant experience alignment": clamp(experience_score),
            "Resume section completeness": clamp(section_ratio * 100),
            "Quantified achievements": clamp(achievement_score),
            "Education and certification relevance": clamp(education_cert_score),
            "ATS readability and formatting": clamp(readability),
            "Contact-information completeness": clamp(contact_score),
        }
        weights = JD_WEIGHTS
    else:
        skills_score = 100 if sections["skills"] else min(len(analysis["resume_keywords"]) * 5, 80)
        section_scores = {
            "Essential section completeness": clamp(section_ratio * 100),
            "Skills coverage and clarity": clamp(skills_score),
            "Experience quality": clamp(experience_score),
            "Quantified achievements": clamp(achievement_score),
            "ATS readability": clamp(readability),
            "Education and certifications": clamp(education_cert_score),
            "Contact-information completeness": clamp(contact_score),
        }
        weights = GENERAL_WEIGHTS

    total = 0
    for score, weight in zip(section_scores.values(), weights.values()):
        total += score * weight / 100
    recommendations = build_recommendations(section_scores, analysis)
    strengths = build_strengths(section_scores, analysis)
    priority_recommendations = prioritize_recommendations(section_scores, analysis)
    overall = clamp(total)
    return {
        **analysis,
        "overall_score": overall,
        "score_band": score_band(overall),
        "section_scores": section_scores,
        "recommendations": recommendations,
        "strengths": strengths,
        "priority_recommendations": priority_recommendations,
        "rubric": weights,
        "summary": "Advisory compatibility score, not a guarantee of employer or ATS acceptance.",
    }


def build_strengths(section_scores, analysis):
    strengths = [name for name, value in section_scores.items() if value >= 80]
    if analysis["matched_keywords"]:
        strengths.append(f"Matched {len(analysis['matched_keywords'])} target keywords.")
    if analysis["quantified_achievement_count"]:
        strengths.append(f"Found {analysis['quantified_achievement_count']} quantified achievements.")
    if all(analysis["contact"].values()):
        strengths.append("Contact information includes email, phone, and professional links.")
    return strengths[:6]


def prioritize_recommendations(section_scores, analysis):
    high = []
    medium = []
    for name, value in section_scores.items():
        if value < 50:
            high.append(f"Prioritize {name.lower()}; this is materially reducing the score.")
        elif value < 75:
            medium.append(f"Strengthen {name.lower()} with more specific evidence.")
    if analysis["missing_keywords"]:
        high.append("Add truthful experience for the most important missing job-description keywords.")
    if analysis["warnings"]["keyword_stuffing"]:
        high.append("Reduce repeated keywords; ATS systems may treat stuffing as a quality signal.")
    if analysis["warnings"]["long_paragraphs"]:
        medium.append("Break long paragraphs into concise bullets for better parsing.")
    return {"high": high[:5], "medium": medium[:5]}


def build_recommendations(section_scores, analysis):
    recs = []
    for name, value in section_scores.items():
        if value < 70:
            recs.append(f"Improve {name.lower()} with clearer evidence and targeted wording.")
    if analysis["missing_keywords"]:
        recs.append("Add truthful examples for missing target keywords where you have experience.")
    if analysis["quantified_achievement_count"] == 0:
        recs.append("Add measurable impact such as percentages, counts, time saved, or revenue influenced.")
    return recs[:8]
