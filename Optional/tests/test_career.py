from app.career.engine import recommend_careers
from app.models import CareerAssessment
from tests.conftest import create_user, login_session


def test_engine_uses_all_inputs():
    low = recommend_careers("python sql", "data science", 1, "")
    high = recommend_careers("python sql", "data science", 10, "ibm data science")
    assert high["top"]["match_percentage"] > low["top"]["match_percentage"]


def test_assessment_created_for_user(auth_client, app):
    response = auth_client.post(
        "/career/assess",
        data={"skills": "Python SQL pandas", "interests": "data science", "cgpa": "8.5", "certifications": "IBM Data Science"},
        follow_redirects=True,
    )
    assert b"Best match" in response.data
    with app.app_context():
        assert CareerAssessment.query.count() == 1


def test_cross_user_assessment_hidden(app):
    first = app.test_client()
    first_id = "16528414-05b2-48fa-b60d-54a296105ad3"
    create_user(app, first_id, "a@example.com")
    login_session(first, first_id)
    first.post("/career/assess", data={"skills": "python", "interests": "ai", "cgpa": "8", "certifications": ""})

    second = app.test_client()
    second_id = "22416c50-47c9-473f-bec5-7740d786475b"
    create_user(app, second_id, "b@example.com")
    login_session(second, second_id)
    assert second.get("/career/result/1").status_code == 404
