import json


def load_json_file(file_name, expected_type):
    """JSON 파일을 읽고 초보자가 이해하기 쉬운 오류를 안내합니다."""
    try:
        with open(file_name, "r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"오류: {file_name} 파일이 없습니다. 프로젝트 폴더에 파일을 추가해주세요.")
        return None
    except json.JSONDecodeError as error:
        print(
            f"오류: {file_name}의 JSON 형식이 올바르지 않습니다. "
            f"{error.lineno}번째 줄의 쉼표나 따옴표를 확인해주세요."
        )
        return None

    if not isinstance(data, expected_type):
        expected_name = "JSON 객체({})" if expected_type is dict else "JSON 배열([])"
        print(f"오류: {file_name}의 최상위 구조는 {expected_name}이어야 합니다.")
        return None

    return data


profile = load_json_file("profile.json", dict)
jobs = load_json_file("jobs.json", list)

if profile is None or jobs is None:
    raise SystemExit(1)

print("=" * 50)
print("RE:START JOB FINDER")
print("=" * 50)
print("채용공고 분석 시스템을 시작합니다.")
print()

# 지원자 정보는 profile.json에서 읽습니다.
applicant_experience_months = profile["total_experience_months"]
applicant_core_experience = profile["core_experience"]
experience_aliases = profile.get("experience_aliases", {})

# 기존 경력 항목 중 같은 경력군에 속하는 이름을 연결합니다.
experience_alias_groups = {
    "가맹사업 운영": "가맹사업",
    "매출정산": "정산",
    "PG": "정산"
}

# 각 영역은 최대점수가 정해져 있습니다.
# 한 영역에서 한 가지 경험만 공고와 맞으면 부분점수,
# 서로 다른 경험이 두 가지 이상 맞으면 해당 영역의 만점을 줍니다.
# 별칭은 띄어쓰기 차이나 비슷한 공고 표현을 인식하기 위한 목록입니다.
career_areas = [
    ("직무 수행 경험", 12, [
        "영업관리", "영업지원", "영업실적관리", "가맹사업 운영",
        "사업운영", "경영관리"
    ]),
    ("시스템·재무 운영", 10, [
        "SAP ERP", "매출관리", "비용관리", "예산관리", "손익관리",
        "PG", "매출정산"
    ]),
    ("성과·관리 역량", 8, [
        "KPI", "지역별 실적관리", "가맹점별 실적관리", "매출 개선", "비용 절감"
    ])
]

# 직무 우선순위도 profile.json에서 읽습니다.
job_priorities = [
    (item["name"], item["score"], item["keywords"])
    for item in profile["job_priorities"]
]


def calculate_career_score(main_tasks):
    """별칭을 포함해 공고 주요업무와 핵심경력을 영역별로 비교합니다."""
    if main_tasks is None:
        return None, []

    normalized_tasks = "".join(main_tasks.split())
    candidates = []

    for area_name, max_points, skills in career_areas:
        for skill_name in skills:
            # 지원자의 핵심경력에 있는 항목만 공고와 비교합니다.
            if skill_name not in applicant_core_experience[area_name]:
                continue

            alias_group = experience_alias_groups.get(skill_name, skill_name)
            aliases = experience_aliases.get(alias_group, [skill_name])

            for alias in aliases:
                normalized_alias = "".join(alias.split())
                if not normalized_alias:
                    continue

                # 각 별칭이 실제 업무 문구의 어느 위치에 나타나는지 기록합니다.
                start = 0
                while True:
                    start = normalized_tasks.find(normalized_alias, start)
                    if start == -1:
                        break
                    candidates.append(
                        (start, start + len(normalized_alias), area_name, alias_group)
                    )
                    start += 1

    # 겹치는 위치의 별칭은 긴 표현을 우선해 한 번만 인정합니다.
    candidates.sort(key=lambda item: item[1] - item[0], reverse=True)
    selected_matches = []
    for candidate in candidates:
        start, end, area_name, alias_group = candidate
        overlaps = False
        for selected in selected_matches:
            selected_start, selected_end, selected_area, selected_group = selected
            if start < selected_end and selected_start < end:
                overlaps = True
                break
        if not overlaps:
            selected_matches.append(candidate)

    total_score = 0
    matched_experience = []
    for area_name, max_points, skills in career_areas:
        matched_in_area = []
        for skill_name in skills:
            if skill_name not in applicant_core_experience[area_name]:
                continue

            alias_group = experience_alias_groups.get(skill_name, skill_name)
            for match_area, match_group in [
                (item[2], item[3]) for item in selected_matches
            ]:
                if match_area == area_name and match_group == alias_group:
                    if alias_group not in matched_in_area:
                        matched_in_area.append(alias_group)
                    break

        # 중복 키워드마다 점수를 더하지 않고, 영역별 일치 수준으로 계산합니다.
        if len(matched_in_area) == 1:
            area_score = max_points // 2
        elif len(matched_in_area) >= 2:
            area_score = max_points
        else:
            area_score = 0

        total_score += area_score
        matched_experience.extend(matched_in_area)

    return total_score, matched_experience


def calculate_year_score(required_min_months):
    """최소 요구경력과 비교해 연차 점수와 부족 개월을 반환합니다."""
    if required_min_months is None:
        return None, None

    shortfall_months = max(
        required_min_months - applicant_experience_months, 0
    )

    if shortfall_months == 0:
        year_score = 10
    elif shortfall_months <= 12:
        year_score = 8
    elif shortfall_months <= 24:
        year_score = 6
    elif shortfall_months <= 36:
        year_score = 4
    else:
        year_score = 0

    return year_score, shortfall_months


def display_value(value):
    """None인 공고 정보는 0 대신 미확인으로 표시합니다."""
    if value is None:
        return "정보 미확인"
    return value


summary_results = []

for job in jobs:
    job_title = job.get("job_title")
    priority_name = "그 외"
    job_fit_score = None

    if job_title is not None:
        job_fit_score = 0
        for name, points, keywords in job_priorities:
            for keyword in keywords:
                if keyword in job_title:
                    priority_name = name
                    job_fit_score = points
                    break
            if job_fit_score > 0:
                break

    career_score, matched_experience = calculate_career_score(job.get("main_tasks"))
    year_score, shortfall_months = calculate_year_score(
        job.get("required_experience_min_months")
    )

    # 점수는 평가 근거가 있을 때만 입력합니다. None은 미확인 항목입니다.
    score_items = [
        ("직무 적합도", job_fit_score, 30),
        ("경력 적합도", career_score, 30),
        ("경력연차", year_score, 10),
        ("지역", job.get("location_score"), 10),
        ("매출액", job.get("revenue_score"), 10),
        ("영업이익", job.get("operating_profit_score"), 10)
    ]

    confirmed_max_score = sum(
        max_points for name, score, max_points in score_items
        if score is not None
    )
    preliminary_score = sum(
        score for name, score, max_points in score_items
        if score is not None
    )
    completion_rate = confirmed_max_score

    if confirmed_max_score > 0:
        converted_score = round(preliminary_score / confirmed_max_score * 100)
    else:
        converted_score = None

    unknown_score_items = [
        name for name, score, max_points in score_items if score is None
    ]

    exclusion_reasons = []
    if job.get("exclusion_reason"):
        exclusion_reasons.append(job.get("exclusion_reason"))

    year_check_note = ""

    # 필수라고 명시되어 있고 13개월 이상 부족한 경우에만 지원 불가입니다.
    if (
        job.get("required_experience_is_mandatory") is True
        and shortfall_months is not None
        and shortfall_months >= 13
    ):
        exclusion_reasons.append(
            f"필수 경력보다 {shortfall_months}개월 부족"
        )
    elif shortfall_months is not None and shortfall_months > 0:
        year_check_note = f"확인 필요: 요구경력보다 {shortfall_months}개월 부족"

    missing_job_fields = [
        label for key, label in [
            ("company", "회사명"),
            ("posting_title", "공고명"),
            ("job_title", "직무명"),
            ("main_tasks", "주요업무"),
            ("required_experience_min_months", "필수경력 최소 개월"),
            ("required_experience_max_months", "필수경력 최대 개월"),
            ("location", "근무지역"),
            ("work_type", "출근방식"),
            ("employment_type", "고용형태"),
            ("revenue", "회사 매출액"),
            ("revenue_trend", "최근 3년 매출 추이"),
            ("operating_profit", "영업이익"),
            ("operating_margin", "영업이익률"),
            ("operating_profit_trend", "최근 3년 영업이익 추이"),
            ("required_qualifications", "필수자격"),
            ("preferred_qualifications", "우대사항"),
            ("education", "학력"),
            ("url", "공고 URL")
        ]
        if job.get(key) is None
    ]

    if exclusion_reasons:
        final_result = "지원 불가"
        notes = "; ".join(exclusion_reasons)
    else:
        if unknown_score_items:
            final_result = "추가 확인 필요"
        else:
            if preliminary_score >= 75:
                final_result = "적극 지원"
            elif preliminary_score >= 65:
                final_result = "지원 추천"
            elif preliminary_score >= 55:
                final_result = "검토"
            else:
                final_result = "비추천"

        notes_to_check = []
        if year_check_note:
            notes_to_check.append(year_check_note)
        if unknown_score_items:
            notes_to_check.append(
                "평가항목 확인 필요: " + ", ".join(unknown_score_items)
            )
        if missing_job_fields:
            notes_to_check.append(
                "공고 정보 확인 필요: " + ", ".join(missing_job_fields)
            )
        notes = "; ".join(notes_to_check) if notes_to_check else "없음"

    # 상세 평가에 사용한 결과를 우선순위 요약용으로 저장합니다.
    reason_parts = []
    if job_fit_score is not None:
        reason_parts.append(f"직무 {priority_name}")
    if career_score is not None:
        reason_parts.append(f"경력 적합도 {career_score}/30점")
    if unknown_score_items:
        if "매출액" in unknown_score_items or "영업이익" in unknown_score_items:
            reason_parts.append("회사 재무정보 확인 필요")
        if "지역" in unknown_score_items:
            reason_parts.append("근무지역 정보 확인 필요")
    if exclusion_reasons:
        reason_parts.append("제외사유 있음")

    fit_percent = converted_score
    information_reliability = completion_rate

    if exclusion_reasons:
        support_status = "지원 불가"
    elif information_reliability < 50:
        support_status = "보류 - 정보 부족"
    elif fit_percent is not None and fit_percent >= 80:
        support_status = "A - 우선 검토"
    elif fit_percent is not None and fit_percent >= 65:
        support_status = "B - 검토"
    elif fit_percent is not None and fit_percent >= 50:
        support_status = "C - 신중 검토"
    else:
        support_status = "D - 비추천"

    summary_results.append({
        "company": job.get("company"),
        "job_title": job.get("job_title"),
        "priority_name": priority_name,
        "job_fit_score": job_fit_score,
        "preliminary_score": preliminary_score,
        "confirmed_max_score": confirmed_max_score,
        "completion_rate": completion_rate,
        "information_reliability": information_reliability,
        "fit_percent": fit_percent,
        "support_status": support_status,
        "has_unknown": bool(unknown_score_items),
        "is_excluded": bool(exclusion_reasons),
        "final_result": final_result,
        "reason": " / ".join(reason_parts) if reason_parts else "평가정보 확인 필요"
    })

    print(f"회사명: {display_value(job.get('company'))}")
    print(f"공고명: {display_value(job.get('posting_title'))}")
    print(f"직무명: {display_value(job.get('job_title'))}")
    print(f"주요업무: {display_value(job.get('main_tasks'))}")
    print(
        "필수경력: "
        f"{display_value(job.get('required_experience_min_months'))}개월 이상 ~ "
        f"{display_value(job.get('required_experience_max_months'))}개월 이하"
    )
    print(f"근무지역: {display_value(job.get('location'))}")
    print(f"출근방식: {display_value(job.get('work_type'))}")
    print(f"고용형태: {display_value(job.get('employment_type'))}")
    print(f"회사 매출액: {display_value(job.get('revenue'))}")
    print(f"최근 3년 매출 추이: {display_value(job.get('revenue_trend'))}")
    print(f"영업이익: {display_value(job.get('operating_profit'))}")
    print(f"영업이익률: {display_value(job.get('operating_margin'))}")
    print(
        "최근 3년 영업이익 추이: "
        f"{display_value(job.get('operating_profit_trend'))}"
    )
    print(f"필수자격: {display_value(job.get('required_qualifications'))}")
    print(f"우대사항: {display_value(job.get('preferred_qualifications'))}")
    print(f"학력: {display_value(job.get('education'))}")
    print(f"공고 URL: {display_value(job.get('url'))}")
    print()

    for name, score, max_points in score_items:
        if score is None:
            print(f"{name}: 정보 미확인 / {max_points}점")
        else:
            print(f"{name}: {score}/{max_points}점")

    if confirmed_max_score > 0:
        print(
            f"잠정점수: {preliminary_score}/{confirmed_max_score}점"
        )
        print(
            f"확인완료 비율: {completion_rate}% "
            f"({confirmed_max_score}/100점 항목 확인)"
        )
        print(f"환산점수: {converted_score}점 (참고용)")
    else:
        print("잠정점수: 정보 미확인")
        print("확인완료 비율: 0%")
        print("환산점수: 정보 미확인")

    if unknown_score_items:
        print("총점: 정보 미확인 (평가정보 확인 후 계산)")
    else:
        print(f"총점: {preliminary_score}/100점")

    print(f"최종판정: {final_result}")
    if job.get("main_tasks") is None:
        matched_text = "정보 미확인"
    else:
        matched_text = ", ".join(matched_experience) if matched_experience else "일치 항목 없음"
    print(f"매칭된 핵심경력: {matched_text}")
    print(f"제외사유 또는 확인 필요사항: {notes}")
    print()

print("SYSTEM READY")


def summary_sort_key(result):
    """지원 가능 여부, 신뢰도, 상태, 적합도 순으로 공고를 정렬합니다."""
    information_reliability = result["information_reliability"]
    fit_percent = result["fit_percent"]
    job_fit_score = result["job_fit_score"]
    if fit_percent is None:
        fit_percent = -1
    if job_fit_score is None:
        job_fit_score = -1

    if result["is_excluded"]:
        return (
            2,
            0,
            0,
            0,
            0
        )

    if information_reliability < 50:
        status_order = 4
        reliability_group = 1
    else:
        status_order = {
            "A - 우선 검토": 0,
            "B - 검토": 1,
            "C - 신중 검토": 2,
            "D - 비추천": 3
        }.get(result["support_status"], 4)
        reliability_group = 0

    return (
        reliability_group,
        status_order,
        -fit_percent,
        -information_reliability,
        -job_fit_score
    )


print("=" * 40)
print("RE:START 지원 우선순위")
print("=" * 40)

summary_results.sort(key=summary_sort_key)

for rank, result in enumerate(summary_results, start=1):
    print()
    print(
        f"{rank}위 | {display_value(result['company'])} | "
        f"{display_value(result['job_title'])}"
    )
    if result["fit_percent"] is None:
        print("적합도 : 정보 미확인")
    else:
        print(f"적합도 : {result['fit_percent']}%")

    print(f"정보 신뢰도 : {result['information_reliability']}%")
    print(f"상태 : {result['support_status']}")

    if result["confirmed_max_score"] > 0:
        print(
            f"잠정점수 : {result['preliminary_score']}/"
            f"{result['confirmed_max_score']}점"
        )
    else:
        print("잠정점수 : 정보 미확인")

    print(f"확인완료 : {result['information_reliability']}%")
    print(f"핵심이유 : {result['reason']}")