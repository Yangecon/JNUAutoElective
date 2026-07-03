"""HTTP client for JNU elective APIs."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional

import requests

from .config import (
    PUBLIC_COURSE_URL,
    REQUEST_TIMEOUT,
    TEACHING_CLASS_TYPE,
    VOLUNTEER_URL,
)
from .credentials import Credentials


class ApiError(Exception):
    """Raised when an API request fails or returns unusable data."""


@dataclass(frozen=True)
class CourseInfo:
    name: str
    course_number: str
    teaching_class_id: str
    campus: str
    campus_name: str
    teacher: str
    place: str
    department: str = ""
    time_text: str = ""
    weeks: str = ""
    schedule_text: str = ""
    schedule_items: list[dict[str, Any]] = field(default_factory=list)

    @property
    def summary(self) -> str:
        return (
            f"{self.name} | 课程号 {self.course_number} | 教学班号 {self.teaching_class_id} | "
            f"{self.campus_name} | {self.teacher} | {self.department} | "
            f"{self.schedule_text or self.time_text} | {self.place}"
        )


def _first_text(raw: dict[str, Any], keys: Iterable[str]) -> str:
    for key in keys:
        value = raw.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def _parse_weekday(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    text = str(value)
    if text.isdigit():
        number = int(text)
        return number if 1 <= number <= 7 else None
    aliases = {
        "一": 1,
        "二": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "日": 7,
        "天": 7,
        "Mon": 1,
        "Tue": 2,
        "Wed": 3,
        "Thu": 4,
        "Fri": 5,
        "Sat": 6,
        "Sun": 7,
    }
    for label, number in aliases.items():
        if label in text:
            return number
    return None


def _parse_sections(*values: Any) -> tuple[Optional[int], Optional[int]]:
    text = " ".join(str(value) for value in values if value not in (None, ""))
    if not text:
        return None, None
    section_match = re.search(r"第\s*(\d+)\s*(?:[-~至到,，、]\s*(\d+))?\s*节", text)
    if section_match:
        start = int(section_match.group(1))
        end = int(section_match.group(2) or start)
        return max(1, min(13, start)), max(start, min(13, end))
    numbers = [int(item) for item in re.findall(r"\d+", text)]
    if not numbers:
        return None, None
    start = max(1, min(13, numbers[0]))
    end = max(start, min(13, numbers[1] if len(numbers) > 1 else start))
    return start, end


def _extract_schedule_items(raw: dict[str, Any], schedule_text: str) -> list[dict[str, Any]]:
    weekday = _parse_weekday(
        raw.get("weekday")
        or raw.get("weekDay")
        or raw.get("dayOfWeek")
        or raw.get("xq")
        or raw.get("skxq")
        or schedule_text
    )
    start, end = _parse_sections(
        raw.get("startSection")
        or raw.get("beginSection")
        or raw.get("startUnit")
        or raw.get("ksjc"),
        raw.get("endSection") or raw.get("endUnit") or raw.get("jsjc"),
        raw.get("section") or raw.get("classSection") or raw.get("jc") or schedule_text,
    )
    if weekday is None or start is None or end is None:
        return []
    return [
        {
            "weekday": weekday,
            "start": start,
            "end": end,
            "label": raw.get("courseName", ""),
            "teacher": raw.get("teacherName", ""),
            "place": raw.get("teachingPlace", ""),
        }
    ]


class CourseClient:
    """Small wrapper around the query and elective submit endpoints."""

    def __init__(self, credentials: Credentials):
        self.credentials = credentials
        self.session = requests.Session()
        self.session.headers.update(credentials.headers)

    def search_class(self, teaching_class_id: str) -> CourseInfo:
        return self.search_course(teaching_class_id)

    def search_course(self, query: str) -> CourseInfo:
        return self.search_courses(query)[0]

    def search_courses(self, query: str) -> list[CourseInfo]:
        query_setting = {
            "data": {
                "studentCode": self.credentials.student_code,
                "campus": "",
                "electiveBatchCode": self.credentials.elective_batch_code,
                "isMajor": "1",
                "teachingClassType": TEACHING_CLASS_TYPE,
                "queryContent": query,
            },
            "pageSize": "10",
            "pageNumber": "0",
            "order": "",
        }
        payload = {"querySetting": json.dumps(query_setting, separators=(",", ":"))}

        try:
            response = self.session.post(PUBLIC_COURSE_URL, data=payload, timeout=REQUEST_TIMEOUT)
            result = response.json()
        except requests.RequestException as exc:
            raise ApiError(f"查询 {query} 请求失败: {exc}") from exc
        except ValueError as exc:
            raise ApiError(f"查询 {query} 返回的不是 JSON。") from exc

        data_list = result.get("dataList") or []
        if not data_list:
            message = result.get("msg") or "无返回信息"
            raise ApiError(f"查询 {query} 无结果: {message}")

        return [_course_from_raw(raw) for raw in data_list]

    def build_add_payload(self, course: CourseInfo) -> dict[str, str]:
        add_param = {
            "data": {
                "operationType": "1",
                "studentCode": self.credentials.student_code,
                "electiveBatchCode": self.credentials.elective_batch_code,
                "teachingClassId": course.teaching_class_id,
                "isMajor": "1",
                "campus": course.campus,
                "teachingClassType": TEACHING_CLASS_TYPE,
            }
        }
        return {"addParam": json.dumps(add_param, separators=(",", ":"))}

    def submit(self, course: CourseInfo) -> object:
        try:
            response = self.session.post(
                VOLUNTEER_URL,
                data=self.build_add_payload(course),
                timeout=REQUEST_TIMEOUT,
            )
            return response.json()
        except requests.RequestException as exc:
            raise ApiError(f"提交 {course.teaching_class_id} 请求失败: {exc}") from exc
        except ValueError as exc:
            raise ApiError(f"提交 {course.teaching_class_id} 返回的不是 JSON。") from exc

    def submit_round(
        self,
        courses: Iterable[CourseInfo],
        *,
        interval: float,
        on_result: Optional[Callable[[CourseInfo, object], None]] = None,
    ) -> None:
        course_list = list(courses)
        for index, course in enumerate(course_list):
            try:
                result = self.submit(course)
            except ApiError as exc:
                result = exc
            if on_result:
                on_result(course, result)
            if index < len(course_list) - 1:
                time.sleep(interval)


def _course_from_raw(raw: dict[str, Any]) -> CourseInfo:
        schedule_text = _first_text(
            raw,
            (
                "teachingTime",
                "classTime",
                "timeAndPlace",
                "teachingTimePlace",
                "courseTime",
                "sksj",
                "sksjdd",
            ),
        )
        return CourseInfo(
            name=raw.get("courseName", ""),
            course_number=raw.get("courseNumber", ""),
            teaching_class_id=raw.get("teachingClassID", ""),
            campus=raw.get("campus", ""),
            campus_name=raw.get("campusName", ""),
            teacher=raw.get("teacherName", ""),
            place=raw.get("teachingPlace", ""),
            department=_first_text(
                raw,
                (
                    "departmentName",
                    "openDepartmentName",
                    "courseDepartmentName",
                    "kkdw",
                    "kkdwmc",
                ),
            ),
            time_text=_first_text(raw, ("time", "timeText", "section", "jc", "classSection")),
            weeks=_first_text(raw, ("weeks", "teachingWeek", "weekDescription", "zcd", "week")),
            schedule_text=schedule_text,
            schedule_items=_extract_schedule_items(raw, schedule_text),
        )


def is_selection_success(result: object) -> bool:
    """Best-effort success detector for elective responses."""
    if isinstance(result, dict):
        for key in ("success", "succeed", "ok"):
            if result.get(key) is True:
                return True
        for key in ("code", "status"):
            value = str(result.get(key, "")).lower()
            if value in {"0", "200", "success", "succeed", "ok"}:
                return True

    text = json.dumps(result, ensure_ascii=False).lower()
    failure_markers = (
        "失败",
        "未成功",
        "错误",
        "异常",
        "已满",
        "冲突",
        "不可",
        "不能",
        "fail",
        "error",
    )
    if any(marker in text for marker in failure_markers):
        return False
    success_markers = (
        "选课成功",
        "抢课成功",
        "添加成功",
        "提交成功",
        "已选",
        "成功",
        "success",
        "succeed",
    )
    return any(marker in text for marker in success_markers)
