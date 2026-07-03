import json

import pytest

from jnu_auto_elective.client import ApiError, CourseClient, CourseInfo, is_selection_success
from jnu_auto_elective.credentials import Credentials


def make_credentials():
    return Credentials(
        cookie="JSESSIONID=abc",
        token="tok",
        student_code="20240001",
        elective_batch_code="BATCH01",
    )


def test_build_add_payload():
    client = CourseClient(make_credentials())
    course = CourseInfo(
        name="线性代数",
        course_number="MA102",
        teaching_class_id="MA102-02",
        campus="2",
        campus_name="番禺校区",
        teacher="李四",
        place="教学楼B202",
    )

    payload = client.build_add_payload(course)
    data = json.loads(payload["addParam"])["data"]

    assert data["studentCode"] == "20240001"
    assert data["electiveBatchCode"] == "BATCH01"
    assert data["teachingClassId"] == "MA102-02"
    assert data["operationType"] == "1"


def test_search_class_success(monkeypatch):
    client = CourseClient(make_credentials())
    captured = {}

    class Response:
        @staticmethod
        def json():
            return {
                "dataList": [
                    {
                        "courseName": "高等数学",
                        "courseNumber": "MA101",
                        "teachingClassID": "MA101-01",
                        "campus": "1",
                        "campusName": "石牌校区",
                        "teacherName": "张三",
                        "teachingPlace": "教学楼A101",
                        "openDepartmentName": "数学学院",
                        "teachingTime": "星期三 第3-4节",
                    }
                ]
            }

    def fake_post(url, data=None, timeout=None):
        captured.update(data)
        return Response()

    monkeypatch.setattr(client.session, "post", fake_post)

    course = client.search_class("MA101-01")

    assert course.name == "高等数学"
    assert course.teaching_class_id == "MA101-01"
    assert course.department == "数学学院"
    assert course.schedule_text == "星期三 第3-4节"
    assert course.schedule_items[0]["weekday"] == 3
    assert course.schedule_items[0]["start"] == 3
    assert course.schedule_items[0]["end"] == 4
    query = json.loads(captured["querySetting"])
    assert query["data"]["queryContent"] == "MA101-01"


def test_search_course_accepts_course_name(monkeypatch):
    client = CourseClient(make_credentials())
    captured = {}

    class Response:
        @staticmethod
        def json():
            return {
                "dataList": [
                    {
                        "courseName": "计量经济学",
                        "courseNumber": "ECON301",
                        "teachingClassID": "ECON301-01",
                        "teacherName": "王五",
                        "departmentName": "经济学院",
                        "campusName": "番禺校区",
                        "teachingPlace": "N101",
                    }
                ]
            }

    def fake_post(url, data=None, timeout=None):
        captured.update(data)
        return Response()

    monkeypatch.setattr(client.session, "post", fake_post)

    course = client.search_course("计量经济学")

    assert course.name == "计量经济学"
    assert course.department == "经济学院"
    query = json.loads(captured["querySetting"])
    assert query["data"]["queryContent"] == "计量经济学"


def test_search_courses_returns_multiple_candidates(monkeypatch):
    client = CourseClient(make_credentials())

    class Response:
        @staticmethod
        def json():
            return {
                "dataList": [
                    {
                        "courseName": "计量经济学",
                        "courseNumber": "ECON301",
                        "teachingClassID": "ECON301-01",
                        "teacherName": "王五",
                    },
                    {
                        "courseName": "计量经济学",
                        "courseNumber": "ECON301",
                        "teachingClassID": "ECON301-02",
                        "teacherName": "赵六",
                    },
                ]
            }

    monkeypatch.setattr(client.session, "post", lambda *args, **kwargs: Response())

    courses = client.search_courses("计量经济学")

    assert [course.teaching_class_id for course in courses] == ["ECON301-01", "ECON301-02"]
    assert [course.teacher for course in courses] == ["王五", "赵六"]


def test_selection_success_detector():
    assert is_selection_success({"msg": "选课成功"})
    assert is_selection_success({"success": True})
    assert not is_selection_success({"msg": "人数已满，提交失败"})


def test_search_class_empty_result(monkeypatch):
    client = CourseClient(make_credentials())

    class Response:
        @staticmethod
        def json():
            return {"dataList": [], "msg": "未找到课程"}

    monkeypatch.setattr(client.session, "post", lambda *args, **kwargs: Response())

    with pytest.raises(ApiError, match="未找到课程"):
        client.search_class("NOPE")
