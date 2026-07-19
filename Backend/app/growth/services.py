from __future__ import annotations

import re
from io import BytesIO
from statistics import mean

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


APPROVED_LANGUAGE_ORDER = ["Python", "Java", "C", "C++", "R", "PHP", "HTML", "JavaScript"]

APPROVED_LANGUAGE_CATALOG = {
    "Python": {
        "description": "A beginner-friendly language used to learn programming fundamentals clearly.",
        "duration": "12 lessons",
        "url": "https://docs.python.org/3/tutorial/",
        "topics": [
            "Introduction to Python",
            "Variables",
            "Data types",
            "Operators",
            "Conditions",
            "Loops",
            "Functions",
            "Lists",
            "Tuples",
            "Dictionaries",
            "Sets",
            "Basic exception handling",
        ],
    },
    "Java": {
        "description": "A strongly typed language for learning structured programming and basic OOP.",
        "duration": "12 lessons",
        "url": "https://dev.java/learn/",
        "topics": [
            "Introduction to Java",
            "Variables",
            "Data types",
            "Operators",
            "Conditions",
            "Loops",
            "Arrays",
            "Methods",
            "Classes",
            "Objects",
            "Basic object-oriented programming",
            "Exception handling",
        ],
    },
    "C": {
        "description": "A foundational language for understanding memory, functions, arrays, and pointers.",
        "duration": "11 lessons",
        "url": "https://en.cppreference.com/w/c",
        "topics": [
            "Introduction to C",
            "Variables",
            "Data types",
            "Operators",
            "Conditions",
            "Loops",
            "Functions",
            "Arrays",
            "Strings",
            "Structures",
            "Basic pointers",
        ],
    },
    "C++": {
        "description": "A beginner path into programming with classes, objects, and basic OOP concepts.",
        "duration": "12 lessons",
        "url": "https://en.cppreference.com/w/cpp",
        "topics": [
            "Introduction to C++",
            "Variables",
            "Data types",
            "Operators",
            "Conditions",
            "Loops",
            "Functions",
            "Arrays",
            "Classes",
            "Objects",
            "Inheritance",
            "Basic object-oriented programming",
        ],
    },
    "R": {
        "description": "A beginner language for programming basics and simple data analysis.",
        "duration": "11 lessons",
        "url": "https://cran.r-project.org/manuals.html",
        "topics": [
            "Introduction to R",
            "Variables",
            "Data types",
            "Vectors",
            "Lists",
            "Matrices",
            "Data frames",
            "Conditions",
            "Loops",
            "Functions",
            "Basic data analysis",
        ],
    },
    "PHP": {
        "description": "A practical language for learning basic server-side scripting and simple web pages.",
        "duration": "10 lessons",
        "url": "https://www.php.net/manual/en/",
        "topics": [
            "Introduction to PHP",
            "Variables",
            "Data types",
            "Operators",
            "Conditions",
            "Loops",
            "Arrays",
            "Functions",
            "Forms",
            "Basic PHP web pages",
        ],
    },
    "HTML": {
        "description": "The basic markup language for building clear, structured web pages.",
        "duration": "10 lessons",
        "url": "https://developer.mozilla.org/en-US/docs/Web/HTML",
        "topics": [
            "Introduction to HTML",
            "HTML document structure",
            "Headings",
            "Paragraphs",
            "Links",
            "Images",
            "Lists",
            "Tables",
            "Forms",
            "Semantic elements",
        ],
    },
    "JavaScript": {
        "description": "A beginner language for interactivity, events, objects, and basic DOM work.",
        "duration": "11 lessons",
        "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide",
        "topics": [
            "Introduction to JavaScript",
            "Variables",
            "Data types",
            "Operators",
            "Conditions",
            "Loops",
            "Functions",
            "Arrays",
            "Objects",
            "Events",
            "Basic DOM manipulation",
        ],
    },
}

APPROVED_LANGUAGE_ALIASES = {
    "py": "Python",
    "python": "Python",
    "java": "Java",
    "c": "C",
    "c++": "C++",
    "cpp": "C++",
    "r": "R",
    "php": "PHP",
    "html": "HTML",
    "html5": "HTML",
    "javascript": "JavaScript",
    "js": "JavaScript",
}

CODING_PLATFORMS = [
    {
        "name": "Programiz",
        "description": "Beginner tutorials, examples, and online compilers for quick practice.",
        "url": "https://www.programiz.com/",
        "cost": "Free and paid",
        "difficulty": "Beginner",
        "best_for": "Step-by-step language basics and browser-based examples.",
        "supported_languages": APPROVED_LANGUAGE_ORDER,
        "practice_urls": {
            "Python": "https://www.programiz.com/python-programming",
            "Java": "https://www.programiz.com/java-programming",
            "C": "https://www.programiz.com/c-programming",
            "C++": "https://www.programiz.com/cpp-programming",
            "R": "https://www.programiz.com/r",
            "PHP": "https://www.programiz.com/php",
            "HTML": "https://www.programiz.com/html",
            "JavaScript": "https://www.programiz.com/javascript",
        },
    },
    {
        "name": "Exercism",
        "description": "Free code exercises with language tracks and community mentoring.",
        "url": "https://exercism.org/tracks",
        "cost": "Free",
        "difficulty": "Beginner to Intermediate",
        "best_for": "Practice problems after learning a topic in the roadmap.",
        "supported_languages": ["Python", "Java", "C", "C++", "R", "PHP", "JavaScript"],
        "practice_urls": {
            "Python": "https://exercism.org/tracks/python",
            "Java": "https://exercism.org/tracks/java",
            "C": "https://exercism.org/tracks/c",
            "C++": "https://exercism.org/tracks/cpp",
            "R": "https://exercism.org/tracks/r",
            "PHP": "https://exercism.org/tracks/php",
            "JavaScript": "https://exercism.org/tracks/javascript",
        },
    },
    {
        "name": "HackerRank 30 Days of Code",
        "description": "A daily coding challenge path for building consistent problem-solving habits.",
        "url": "https://www.hackerrank.com/domains/tutorials/30-days-of-code",
        "cost": "Free",
        "difficulty": "Beginner",
        "best_for": "Daily practice with conditions, loops, functions, and basic problem solving.",
        "supported_languages": ["Python", "Java", "C", "C++", "JavaScript"],
        "practice_urls": {
            "Python": "https://www.hackerrank.com/domains/tutorials/30-days-of-code",
            "Java": "https://www.hackerrank.com/domains/tutorials/30-days-of-code",
            "C": "https://www.hackerrank.com/domains/tutorials/30-days-of-code",
            "C++": "https://www.hackerrank.com/domains/tutorials/30-days-of-code",
            "JavaScript": "https://www.hackerrank.com/domains/tutorials/30-days-of-code",
        },
    },
    {
        "name": "freeCodeCamp",
        "description": "Free interactive lessons and practice projects for web and programming foundations.",
        "url": "https://www.freecodecamp.org/",
        "cost": "Free",
        "difficulty": "Beginner",
        "best_for": "Structured practice for HTML, JavaScript, and Python foundations.",
        "supported_languages": ["Python", "HTML", "JavaScript"],
        "practice_urls": {
            "Python": "https://www.freecodecamp.org/learn/scientific-computing-with-python/",
            "HTML": "https://www.freecodecamp.org/learn/2022/responsive-web-design/",
            "JavaScript": "https://www.freecodecamp.org/learn/javascript-algorithms-and-data-structures-v8/",
        },
    },
]


def normalize_skill(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9+#./\s-]", " ", value or "").lower().strip()
    text = re.sub(r"\s+", " ", text)
    return APPROVED_LANGUAGE_ALIASES.get(text, text).lower()


def canonical_career(title: str | None) -> str:
    text = re.sub(r"[^a-zA-Z0-9+#./\s-]", " ", title or "").lower().strip()
    text = re.sub(r"\s+", " ", text)
    return APPROVED_LANGUAGE_ALIASES.get(text, "Python")


def get_available_tracks():
    return APPROVED_LANGUAGE_ORDER[:]


def get_coding_platforms(language: str | None = None, search: str | None = None):
    selected_language = canonical_career(language) if language else ""
    search_text = (search or "").strip().lower()
    cards = []
    for platform in CODING_PLATFORMS:
        if selected_language and selected_language not in platform["supported_languages"]:
            continue
        searchable = " ".join(
            [
                platform["name"],
                platform["description"],
                platform["best_for"],
                " ".join(platform["supported_languages"]),
            ]
        ).lower()
        if search_text and search_text not in searchable:
            continue
        practice_url = platform["practice_urls"].get(selected_language) if selected_language else platform["url"]
        cards.append(
            {
                **platform,
                "active_language": selected_language,
                "practice_url": practice_url or platform["url"],
                "supported_languages_text": ", ".join(platform["supported_languages"]),
            }
        )
    return cards


def _topic_key(language: str, topic: str) -> str:
    return normalize_skill(f"{language} {topic}")


def get_career_skills(career_title: str):
    language = canonical_career(career_title)
    topics = APPROVED_LANGUAGE_CATALOG[language]["topics"]
    return [
        {
            "id": f"{normalize_skill(language)}-{index}",
            "name": topic,
            "normalized_name": _topic_key(language, topic),
            "category": "core",
            "description": f"Beginner lesson for {language}: {topic}.",
            "priority": "High",
            "difficulty": "Beginner",
            "prerequisites": [] if index == 1 else [topics[index - 2]],
            "estimated_hours": 1,
            "required": True,
            "learning_outcomes": [f"Understand {topic}.", f"Practice {topic} in {language}."],
            "project_suggestion": f"Complete a small {language} exercise for {topic}.",
            "search_keywords": [language.lower(), topic.lower()],
            "applicable_experience_levels": ["complete_beginner", "beginner"],
        }
        for index, topic in enumerate(topics, start=1)
    ]


def parse_skills(value: str | list[str] | None) -> set[str]:
    raw_items = value if isinstance(value, list) else re.split(r"[,;\n|]+", value or "")
    return {normalize_skill(item) for item in raw_items if normalize_skill(item)}


def completed_skill_names(roadmaps) -> set[str]:
    done = set()
    for roadmap in roadmaps or []:
        for stage in roadmap.stages:
            if stage.progress == 100:
                done.add(normalize_skill(stage.skill_name))
            for task in stage.tasks:
                if task.completed:
                    done.add(normalize_skill(task.title))
    return done


def build_roadmap(career_title, known_skills=None, level="beginner", weekly_hours=8, ats_gaps=None, completed_skills=None, target_date=None):
    language = canonical_career(career_title)
    completed = {normalize_skill(item) for item in completed_skills or []}
    known = parse_skills(known_skills)
    topics = APPROVED_LANGUAGE_CATALOG[language]["topics"]
    safe_weekly = max(1, min(int(weekly_hours or 8), 80))
    phases = []
    skills = get_career_skills(language)
    for index, topic in enumerate(topics, start=1):
        topic_key = _topic_key(language, topic)
        status = "Completed" if topic_key in completed or normalize_skill(topic) in completed or normalize_skill(topic) in known else "Not started"
        progress = 100 if status == "Completed" else 0
        phases.append(
            {
                "key": topic_key,
                "level": "Beginner",
                "title": f"Step {index}: {topic}",
                "skill_name": topic,
                "description": f"Learn {topic} in {language} with a simple beginner-friendly explanation.",
                "weeks": 1,
                "hours": 1,
                "required": True,
                "skills": skills[index - 1 : index],
                "statuses": [status],
                "projects": [f"Practice task: create a small {language} example using {topic}."],
                "assessment": f"Explain {topic} and complete one simple {language} practice task.",
                "criteria": f"You can explain {topic} and complete the practice task without copying.",
                "resources": resources_for_skill(language),
                "progress": progress,
                "objectives": [f"Understand {topic}.", f"Practice {topic} in {language}."],
                "prerequisites": [] if index == 1 else [topics[index - 2]],
                "tasks": [
                    {
                        "title": topic,
                        "description": f"Simple practice task: create a small {language} example using {topic}.",
                        "type": "lesson",
                        "resource_url": APPROVED_LANGUAGE_CATALOG[language]["url"],
                        "completed": progress == 100,
                    }
                ],
            }
        )
    return {
        "career": language,
        "estimated_weeks": len(topics),
        "estimated_hours": len(topics),
        "weekly_hours": safe_weekly,
        "required_weekly_hours": None,
        "date_warning": None,
        "phases": phases,
        "missing_skills": [topic for topic in topics if normalize_skill(topic) not in completed and _topic_key(language, topic) not in completed],
    }


def resources_for_skill(skill_name, skill_item=None, phase_name=""):
    language = canonical_career(skill_name)
    details = APPROVED_LANGUAGE_CATALOG[language]
    return [
        {
            "title": f"{language} Beginner Lessons",
            "provider": "Official Documentation",
            "url": details["url"],
            "type": "Documentation",
            "level": "Beginner",
            "cost_type": "free",
            "priority": "High",
            "duration": details["duration"],
            "skill": language.lower(),
            "description": details["description"],
        }
    ]


def learning_resource_rows_for_plan(plan):
    languages = plan.get("languages") if isinstance(plan, dict) else None
    if not languages:
        phases = plan.get("phases", []) if isinstance(plan, dict) else []
        languages = sorted(
            {
                canonical_career(resource.get("skill"))
                for phase in phases
                if isinstance(phase, dict)
                for resource in phase.get("resources", [])
                if isinstance(resource, dict) and resource.get("skill")
            }
        )
    rows = []
    for language in languages or APPROVED_LANGUAGE_ORDER:
        language = canonical_career(language)
        details = APPROVED_LANGUAGE_CATALOG[language]
        rows.append(
            (
                language.lower(),
                f"{language} Beginner Lessons",
                "Official Documentation",
                "Documentation",
                "Beginner",
                "free",
                "High",
                details["duration"],
                details["url"],
                details["description"],
            )
        )
    return rows


RESOURCE_CATALOG = learning_resource_rows_for_plan({"languages": APPROVED_LANGUAGE_ORDER})


def learning_recommendations(career_title):
    return learning_resource_rows_for_plan(build_roadmap(career_title))


def score_resume_document(content):
    sections = ["summary", "skills", "experience", "education", "projects"]
    section_score = sum(1 for key in sections if content.get(key, "").strip()) / len(sections) * 45
    metrics_score = min(content.get("experience", "").count("%") * 10 + count_numbers(content.get("experience", "")) * 6, 25)
    keyword_score = min(len([s for s in content.get("skills", "").split(",") if s.strip()]) * 4, 20)
    link_score = 10 if "linkedin" in content.get("links", "").lower() or "github" in content.get("links", "").lower() else 4
    score = round(section_score + metrics_score + keyword_score + link_score)
    tips = []
    if section_score < 40:
        tips.append("Complete summary, skills, experience, education, and projects sections.")
    if metrics_score < 15:
        tips.append("Add quantified impact such as percentages, counts, time saved, or revenue influenced.")
    if keyword_score < 16:
        tips.append("Add a focused skill list aligned with the role.")
    if link_score < 10:
        tips.append("Add LinkedIn, GitHub, or portfolio links.")
    return max(0, min(100, score)), tips


def count_numbers(text):
    return sum(ch.isdigit() for ch in text or "")


def resume_pdf(document):
    content = document.content_json
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    _, height = letter
    y = height - 54
    pdf.setTitle(document.title)
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(54, y, content.get("name") or document.title)
    y -= 18
    pdf.setFont("Helvetica", 10)
    pdf.drawString(54, y, f"{content.get('email','')}  {content.get('phone','')}  {content.get('links','')}"[:110])
    y -= 28
    for label, key in [("Summary", "summary"), ("Skills", "skills"), ("Experience", "experience"), ("Projects", "projects"), ("Education", "education")]:
        value = content.get(key, "").strip()
        if not value:
            continue
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(54, y, label)
        y -= 16
        pdf.setFont("Helvetica", 10)
        for line in value.splitlines() or [value]:
            if y < 54:
                pdf.showPage()
                y = height - 54
                pdf.setFont("Helvetica", 10)
            pdf.drawString(62, y, line[:105])
            y -= 14
        y -= 8
    pdf.save()
    buffer.seek(0)
    return buffer


QUESTION_BANK = {
    "technical": [
        "Explain a project where you made an important technical tradeoff.",
        "How would you design a reliable resume analysis workflow?",
        "What testing strategy would you use for an authentication flow?",
    ],
    "hr": [
        "Why are you interested in this role?",
        "Tell me about your strengths and areas for improvement.",
        "How do you handle deadlines and ambiguity?",
    ],
    "behavioral": [
        "Tell me about a conflict you resolved.",
        "Describe a time you learned something quickly.",
        "Give an example of ownership under pressure.",
    ],
    "coding": [
        "Write an approach to find duplicate strings efficiently.",
        "How would you validate a PDF upload safely?",
        "Explain time complexity for searching in a sorted list.",
    ],
    "mcq": [
        "Which HTTP status is used for unauthorized access?",
        "Which loop repeats while a condition remains true?",
        "What does CSRF protection prevent?",
    ],
}


def build_questions(category, difficulty, count=5):
    base = QUESTION_BANK.get(category, QUESTION_BANK["technical"])
    questions = []
    while len(questions) < count:
        questions.extend(base)
    return [{"prompt": q, "difficulty": difficulty, "category": category} for q in questions[:count]]


def evaluate_answers(questions, answers):
    scores = []
    grammar = []
    communication = []
    for answer in answers:
        words = len(answer.split())
        scores.append(min(100, 35 + words * 2 + keyword_bonus(answer)))
        communication.append(min(100, 40 + words))
        grammar.append(88 if answer and answer[0:1].isupper() and answer.rstrip().endswith((".", "!", "?")) else 68)
    technical = round(mean(scores or [0]))
    comm = round(mean(communication or [0]))
    gram = round(mean(grammar or [0]))
    report = (
        f"Technical score {technical}/100, communication score {comm}/100, grammar score {gram}/100. "
        "Use structured answers with context, action, result, and measurable impact."
    )
    return technical, comm, gram, report


def keyword_bonus(answer):
    terms = ["because", "measured", "tested", "designed", "improved", "tradeoff", "result"]
    return sum(5 for term in terms if term in answer.lower())
