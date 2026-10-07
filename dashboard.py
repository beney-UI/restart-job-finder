import json
from datetime import date

JOBS_FILE = "jobs.json"
APPLICATIONS_FILE = "applications.json"
PROFILE_FILE = "profile.json"


def load_json_file(file_name, expected_type, label):
    """JSON 파일을 읽습니다. 문제가 있으면 안내하고 빈 자료로 계속합니다."""
    try:
        with open(file_name, "r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"안내: {label} 파일이 없습니다. 해당 항목은 비어 있는 것으로 표시합니다.")
        return [] if expected_type is list else {}
    except json.JSONDecodeError as error:
        print(
            f"안내: {label} 파일의 JSON 형식이 올바르지 않습니다. "
            f"{error.lineno}번째 줄을 확인해주세요. 해당 항목은 비어 있는 것으로 표시합니다."
        )
        return [] if expected_type is list else {}
    except OSError as error:
        print(f"안내: {label} 파일을 읽을 수 없습니다. {error}")
        return [] if expected_type is list else {}

    if not isinstance(data, expected_type):
        print(f"안내: {label} 파일의 데이터 형식이 올바르지 않습니다.")
        return [] if expected_type is list else {}

    return data


def display(value, default="정보 미확인"):
    """비어 있는 값을 이해하기 쉬운 문구로 바꿉니다."""
    if value is None or value == "":
        return default
    return str(value)


def application_key(application):
    """회사명과 공고명으로 지원 여부를 비교할 기준을 만듭니다."""
    return (
        application.get("company"),
        application.get("posting_title")
    )


def job_priority(job, priorities):
    """공고 직무명과 프로필의 우선순위 키워드를 비교합니다."""
    title = job.get("job_title")
    if not isinstance(title, str):
        return None

    for priority in priorities:
        for keyword in priority.get("keywords", []):
            if keyword in title:
                return priority.get("name")
    return None


def show_job_summary(jobs, priorities):
    """저장된 평가 상태가 있는 경우만 세고, 점수는 새로 계산하지 않습니다."""
    status_counts = {
        "A - 우선 검토": 0,
        "B - 검토": 0,
        "정보 부족": 0
    }

    for job in jobs:
        stored_status = job.get("support_status")
        if stored_status in status_counts:
            status_counts[stored_status] += 1
        elif stored_status is None or stored_status == "보류 - 정보 부족":
            # 현재 jobs.json에는 평가 결과가 저장되지 않아 정보 부족으로 집계합니다.
            status_counts["정보 부족"] += 1

    print("[공고 현황]")
    print(f"등록 공고 : {len(jobs)}건")
    print(f"A - 우선 검토 : {status_counts['A - 우선 검토']}건")
    print(f"B - 검토 : {status_counts['B - 검토']}건")
    print(f"정보 부족 : {status_counts['정보 부족']}건")


def show_application_summary(applications):
    """지원 상태를 요청된 묶음으로 집계해 출력합니다."""
    statuses = [
        application.get("application_status")
        for application in applications
    ]

    planned_count = statuses.count("지원예정")
    completed_count = statuses.count("지원완료")
    document_pass_count = statuses.count("서류합격")
    interview_count = statuses.count("면접예정") + statuses.count("면접완료")
    final_pass_count = statuses.count("최종합격")
    rejected_count = statuses.count("서류탈락") + statuses.count("최종탈락")

    print("[지원 현황]")
    print(f"지원예정 : {planned_count}건")
    print(f"지원완료 : {completed_count}건")
    print(f"서류합격 : {document_pass_count}건")
    print(f"면접진행 : {interview_count}건")
    print(f"최종합격 : {final_pass_count}건")
    print(f"탈락 : {rejected_count}건")


def show_jobs_to_review(jobs, applications, priorities):
    """아직 지원현황에 없는 우선순위 직무를 점수 없이 표시합니다."""
    registered_applications = {
        application_key(application) for application in applications
    }
    priority_order = {
        priority.get("name"): number
        for number, priority in enumerate(priorities)
    }
    jobs_to_review = []

    for index, job in enumerate(jobs):
        priority = job_priority(job, priorities)
        key = (job.get("company"), job.get("posting_title"))

        if priority is not None and key not in registered_applications:
            jobs_to_review.append((priority_order.get(priority, 99), index, job, priority))

    jobs_to_review.sort(key=lambda item: (item[0], item[1]))

    print("[오늘 우선 검토할 공고]")
    if not jobs_to_review:
        print("확인할 미등록 우선순위 공고가 없습니다.")
        return

    for _, _, job, priority in jobs_to_review:
        company = display(job.get("company"))
        job_title = display(job.get("job_title"))
        print(f"- {company} | {job_title} ({priority})")
        print("  평가점수: main.py에서 평가 확인 필요")


def follow_up_for_status(application):
    """지원 상태에 해당하는 후속 조치 문구를 반환합니다."""
    status = application.get("application_status")

    if status == "지원예정":
        return "지원 여부 결정 필요"
    if status == "지원완료":
        return "서류 결과 대기"
    if status == "서류합격":
        return "면접 일정 확인 필요"
    if status == "면접예정":
        interview_date = application.get("interview_date")
        if interview_date:
            return f"면접일: {interview_date}"
        return "면접일 미등록"
    if status == "면접완료":
        return "최종 결과 확인"
    if status == "최종합격":
        return "처우 및 입사조건 확인"
    return None


def show_follow_ups(applications):
    """후속 조치가 정해진 지원내역만 표시합니다."""
    print("[후속조치 필요]")
    found_follow_up = False

    for application in applications:
        follow_up = follow_up_for_status(application)
        if follow_up is None:
            continue

        found_follow_up = True
        company = display(application.get("company"))
        job_title = display(application.get("job_title"))
        print(f"- {company} | {job_title} : {follow_up}")

    if not found_follow_up:
        print("현재 등록된 후속조치가 없습니다.")


def show_today_tasks(applications):
    """지원 상태를 바탕으로 오늘 할 일을 최대 5개까지 표시합니다."""
    task_text = {
        "지원예정": "지원 여부 결정",
        "지원완료": "서류 결과 확인",
        "서류합격": "면접 일정 확인",
        "면접예정": "면접 준비",
        "면접완료": "최종 결과 확인",
        "최종합격": "처우 및 입사조건 확인"
    }
    tasks = []

    for application in applications:
        status = application.get("application_status")
        task = task_text.get(status)
        if task is None:
            continue

        company = display(application.get("company"))
        tasks.append(f"{company} - {task}")

    print("[오늘의 RE:START]")
    if not tasks:
        print("현재 지원현황을 기준으로 표시할 일이 없습니다.")
        return

    for number, task in enumerate(tasks[:5], start=1):
        print(f"{number}. {task}")


def main():
    jobs = load_json_file(JOBS_FILE, list, "채용공고")
    applications = load_json_file(APPLICATIONS_FILE, list, "지원현황")
    profile = load_json_file(PROFILE_FILE, dict, "지원자 프로필")
    priorities = profile.get("job_priorities", [])
    if not isinstance(priorities, list):
        priorities = []

    print("=" * 40)
    print("RE:START JOB SEARCH DASHBOARD")
    print(f"오늘 날짜 : {date.today().isoformat()}")
    print("=" * 40)

    if not jobs:
        print("안내: 등록된 채용공고가 없습니다. jobs.json을 확인해주세요.")
    if not applications:
        print("안내: 등록된 지원내역이 없습니다. applications.json을 확인해주세요.")

    show_job_summary(jobs, priorities)
    print()
    show_application_summary(applications)
    print()
    show_jobs_to_review(jobs, applications, priorities)
    print()
    show_follow_ups(applications)
    print()
    show_today_tasks(applications)

    print("\n" + "-" * 40)
    print("실행 명령어")
    print("공고 평가     : python main.py")
    print("공고 등록     : python add_job.py")
    print("지원현황 관리 : python application_manager.py")
    print("-" * 40)


if __name__ == "__main__":
    main()
