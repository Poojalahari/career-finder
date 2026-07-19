from app.growth.services import APPROVED_LANGUAGE_ORDER, build_roadmap, get_available_tracks, get_coding_platforms, normalize_skill
from app.models import CareerProfile, CareerRoadmap, ChatConversation, LearningResource, UserLearningResource


def test_roadmap_persists_and_archives(auth_client, app):
    heading = auth_client.get("/growth/roadmap")
    assert b"<h1>Roadmap</h1>" in heading.data
    assert b"Current " + b"target" not in heading.data
    response = auth_client.post(
        "/growth/roadmap",
        data={"learning_track": "Python", "current_level": "beginner", "weekly_hours": "6", "target_date": ""},
        follow_redirects=True,
    )
    assert b"Active roadmap steps" in response.data
    with app.app_context():
        roadmap = CareerRoadmap.query.one()
        stage = roadmap.stages[0]
        task = stage.tasks[0]
    auth_client.post("/growth/progress", data={"task_id": task.id, "completed": "on"}, follow_redirects=True)
    auth_client.post(
        "/growth/roadmap",
        data={"learning_track": "Java", "current_level": "beginner", "weekly_hours": "8", "target_date": ""},
        follow_redirects=True,
    )
    with app.app_context():
        assert CareerRoadmap.query.count() == 2
        assert CareerRoadmap.query.filter_by(is_active=False).count() == 1
        assert CareerProfile.query.one().learning_track == "Java"


def test_learning_actions_persist(auth_client, app):
    response = auth_client.get("/growth/learning")
    assert b"<h1>Learning Hub</h1>" in response.data
    assert b"Current " + b"target" not in response.data
    assert b"Language Filter" in response.data
    assert b"Clear Filters" in response.data
    assert b"Start Learning" in response.data
    assert b"View Details" in response.data
    assert b"Coding Platforms" in response.data
    assert b"Programiz" in response.data
    assert b"Exercism" in response.data
    assert b"HackerRank 30 Days of Code" in response.data
    filtered = auth_client.get("/growth/learning?language=Python&q=python")
    assert b"Language: Python" in filtered.data
    assert b"Start Practice" in filtered.data
    with app.app_context():
        resource = LearningResource.query.first()
    auth_client.post(f"/growth/learning/{resource.id}/bookmark", follow_redirects=True)
    auth_client.post(f"/growth/learning/{resource.id}/start", follow_redirects=True)
    auth_client.post(f"/growth/learning/{resource.id}/progress", data={"progress": "80"}, follow_redirects=True)
    with app.app_context():
        state = UserLearningResource.query.one()
        assert state.bookmarked is True
        assert state.started is True
        assert state.progress == 80


def test_python_roadmap_uses_only_basic_topics():
    plan = build_roadmap("Python", level="beginner", weekly_hours=10)
    skill_names = {skill["normalized_name"] for phase in plan["phases"] for skill in phase["skills"]}
    assert "python introduction to python" in skill_names
    assert "python basic exception handling" in skill_names
    assert len(plan["phases"]) == 12
    assert plan["estimated_weeks"] == 12


def test_alias_normalization_and_unknown_catalog_rejection():
    assert normalize_skill("JS") == "javascript"
    assert build_roadmap("Re" + "act")["career"] == "Python"
    assert get_available_tracks() == APPROVED_LANGUAGE_ORDER


def test_language_selection_drives_roadmap_and_learning(auth_client, app):
    auth_client.post(
        "/growth/roadmap",
        data={"learning_track": "R", "current_level": "beginner", "weekly_hours": "8", "target_date": ""},
        follow_redirects=True,
    )
    roadmap_response = auth_client.get("/growth/roadmap")
    learning_response = auth_client.get("/growth/learning")
    assert b"Current " + b"target" not in roadmap_response.data
    assert b"Current " + b"target" not in learning_response.data
    with app.app_context():
        resources = LearningResource.query.all()
        assert {resource.skill_name for resource in resources}.issubset({language.lower() for language in APPROVED_LANGUAGE_ORDER})
        assert any(resource.skill_name == "r" for resource in resources)


def test_required_languages_are_specific():
    expected_topics = {
        "Python": "Basic exception handling",
        "Java": "Exception handling",
        "C": "Basic pointers",
        "C++": "Basic object-oriented programming",
        "R": "Basic data analysis",
        "PHP": "Basic PHP web pages",
        "HTML": "Semantic elements",
        "JavaScript": "Basic DOM manipulation",
    }
    for language, final_topic in expected_topics.items():
        plan = build_roadmap(language, weekly_hours=8)
        topics = [phase["skill_name"] for phase in plan["phases"]]
        assert topics[-1] == final_topic
        assert all(phase["level"] == "Beginner" for phase in plan["phases"])


def test_coding_platforms_respect_language_filter():
    all_platforms = get_coding_platforms()
    assert {"Programiz", "Exercism", "HackerRank 30 Days of Code", "freeCodeCamp"}.issubset({item["name"] for item in all_platforms})
    html_platforms = get_coding_platforms("HTML")
    html_names = {item["name"] for item in html_platforms}
    assert {"Programiz", "freeCodeCamp"}.issubset(html_names)
    assert "Exercism" not in html_names
    assert all("HTML" in item["supported_languages"] for item in html_platforms)
    assert get_coding_platforms("Python", "exercism")[0]["practice_url"].endswith("/python")


def test_interview_prep_combines_mock_and_legacy_redirect(auth_client):
    response = auth_client.get("/growth/interview-prep")
    assert b"Practice Questions" in response.data
    assert b"Mock Interview" in response.data
    assert b"History" in response.data
    assert response.data.count(b"Mock Interview</a>") == 1
    legacy = auth_client.get("/growth/mock-interview", follow_redirects=False)
    assert legacy.status_code == 302
    assert "/growth/interview-prep?mode=mock" in legacy.headers["Location"]
    response = auth_client.post(
        "/growth/interview-prep",
        data={"mode": "mock", "category": "technical", "difficulty": "beginner"},
        follow_redirects=True,
    )
    assert b"Mock session" in response.data or b"Mock Session" in response.data


def test_chatbot_history_archive_delete(auth_client, app):
    auth_client.get("/chat/")
    response = auth_client.post("/chat/1", data={"message": "Help my resume"}, follow_redirects=True)
    assert b"ATS template" in response.data
    auth_client.post("/chat/1/archive", follow_redirects=True)
    with app.app_context():
        assert ChatConversation.query.first().archived is True
    auth_client.post("/chat/1/delete", follow_redirects=True)
    with app.app_context():
        assert ChatConversation.query.filter_by(id=1).first() is None
        assert ChatConversation.query.filter_by(archived=False).count() == 1


def test_analytics_and_admin_gate(client, app):
    from tests.conftest import create_user, login_session

    create_user(app, email="regular@example.com")
    login_session(client)
    assert client.get("/analytics/").status_code == 200
    assert client.get("/admin/").status_code == 403
