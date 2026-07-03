"""Shared configuration constants."""

BASE_URL = "https://jwxk.jnu.edu.cn/"

XKXF_URL = f"{BASE_URL}xsxkapp/sys/xsxkapp/student/xkxf.do"
PUBLIC_COURSE_URL = f"{BASE_URL}xsxkapp/sys/xsxkapp/elective/publicCourse.do"
VOLUNTEER_URL = f"{BASE_URL}xsxkapp/sys/xsxkapp/elective/volunteer.do"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

TEACHING_CLASS_TYPE = "QXKC"
DEFAULT_BROWSER_TIMEOUT = 120
DEFAULT_ROUNDS = 3
DEFAULT_INTERVAL = 1.0
REQUEST_TIMEOUT = 10
