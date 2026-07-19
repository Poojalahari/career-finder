def career_reply(message, latest_career=None):
    text = message.lower()
    career = latest_career or "your target role"
    if any(word in text for word in ["resume", "cv", "ats"]):
        return (
            "For resume improvement, use a clean ATS template, lead with measurable impact, "
            "match truthful keywords from the job description, and keep sections named Summary, Skills, Experience, Projects, and Education."
        )
    if any(word in text for word in ["interview", "hr", "behavioral", "mock"]):
        return (
            "For interview prep, practice STAR answers: situation, task, action, result. "
            "For technical rounds, explain tradeoffs, complexity, tests, and production risks."
        )
    if any(word in text for word in ["learn", "course", "book", "youtube", "resource"]):
        return (
            f"For {career}, start with fundamentals, then build projects, then review official docs. "
            "Prioritize free docs and practice platforms first, then paid courses only for structured depth."
        )
    if any(word in text for word in ["project", "portfolio", "github"]):
        return (
            f"Strong {career} projects should solve a real problem, include a README, tests, deployment notes, "
            "and measurable outcomes. Add screenshots or a live demo when possible."
        )
    if any(word in text for word in ["roadmap", "career", "path", "switch"]):
        return (
            f"A practical path toward {career}: validate prerequisites, close skill gaps, build two portfolio projects, "
            "prepare role-specific interview stories, and tailor your resume for each application."
        )
    return (
        "I can help with career guidance, resume assistance, interview preparation, learning recommendations, "
        "and project suggestions. Tell me your target role and current skills for a more specific plan."
    )
