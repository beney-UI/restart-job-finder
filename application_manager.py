import json
import os
from datetime import datetime

JOBS_FILE = "jobs.json"
APPLICATIONS_FILE = "applications.json"

# 지원현황에서 사용할 수 있는 상태 목록입니다.
APPLICATION_STATUSES = [
    "지원예정",
    "지원완료",
    "서류합격",
    "서류탈락",
    "면접예정",
    "면접완료",
    "최종합격",
    "최종탈락",
    "지원취소"
]


# applications.json이 없을 때만 빈 배열 파일을 만듭니다.
def create_empty_applications_file():
    try:
        with open(APPLICATIONS_FILE, "w", encoding="utf-8") as file:
            json.dump([], file, ensure_ascii=False, indent=2)
        return True
    except OSError as error:
        print(f"오류: 지원현황 파일을 만들 수 없습니다. {error}")
        return False


# JSON 파일을 읽습니다. 형식이 잘못된 파일은 덮어쓰지 않습니다.
def load_json_file(file_name, expected_type, description):
    try:
        with open(file_name, "r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        if file_name == APPLICATIONS_FILE:
            if create_empty_applications_file():
                return []
            return None

        print(f"오류: {description} 파일({file_name})을 찾을 수 없습니다.")
        return None
    except json.JSONDecodeError as error:
        print(
            f"오류: {description} 파일의 JSON 형식이 잘못되었습니다. "
            f"{error.lineno}번째 줄을 확인해주세요. 기존 파일은 변경하지 않았습니다."
        )
        return None
    except OSError as error:
        print(f"오류: {description} 파일을 읽을 수 없습니다. {error}")
        return None

    if not isinstance(data, expected_type):
        expected_name = "배열([])" if expected_type is list else "객체({})"
        print(f"오류: {description} 파일의 최상위 구조는 {expected_name}이어야 합니다.")
        return None

    return data


# 입력한 날짜가 실제 YYYY-MM-DD 형식인지 확인합니다.
def ask_date(prompt):
    while True:
        value = input(prompt).strip()
        if value == "":
            return None

        try:
            parsed_date = datetime.strptime(value, "%Y-%m-%d")
            if parsed_date.strftime("%Y-%m-%d") == value:
                return value
        except ValueError:
            pass

        print("날짜는 YYYY-MM-DD 형식으로 입력해주세요. 예: 2026-10-07")


# 번호를 입력받아 목록에서 선택할 수 있게 합니다.
def choose_item(items, prompt):
    while True:
        value = input(prompt).strip()
        if not value.isdigit():
            print("번호를 입력해주세요.")
            continue

        number = int(value)
        if 1 <= number <= len(items):
            return number - 1

        print(f"1부터 {len(items)} 사이의 번호를 입력해주세요.")


# 지원상태를 목록으로 보여주고 선택받습니다.
def choose_status():
    print("지원상태를 선택하세요:")
    for number, status in enumerate(APPLICATION_STATUSES, start=1):
        print(f"{number}. {status}")

    index = choose_item(APPLICATION_STATUSES, "상태 번호: ")
    return APPLICATION_STATUSES[index]


# 안전하게 applications.json에 저장합니다.
def save_applications(applications):
    try:
        with open(APPLICATIONS_FILE, "w", encoding="utf-8") as file:
            json.dump(applications, file, ensure_ascii=False, indent=2)
        return True
    except OSError as error:
        print(f"오류: 지원현황을 저장할 수 없습니다. {error}")
        return False


def get_job_value(job, key):
    """공고에 필드가 없거나 null이면 안내용 문구를 반환합니다."""
    value = job.get(key)
    if value is None or value == "":
        return "정보 미확인"
    return value


def is_duplicate_application(applications, company, posting_title):
    """회사명과 공고명이 모두 같은 지원내역이 있는지 확인합니다."""
    for application in applications:
        if (
            application.get("company") == company
            and application.get("posting_title") == posting_title
        ):
            return True
    return False


def register_application(applications):
    jobs = load_json_file(JOBS_FILE, list, "채용공고")
    if jobs is None:
        return applications

    if not jobs:
        print("등록할 채용공고가 없습니다.")
        return applications

    print("\n채용공고 목록")
    for number, job in enumerate(jobs, start=1):
        company = get_job_value(job, "company")
        job_title = get_job_value(job, "job_title")
        print(f"{number}. {company} | {job_title}")
    print("0. 취소")

    while True:
        value = input("지원할 공고 번호: ").strip()
        if value == "0":
            print("지원 등록을 취소했습니다.")
            return applications
        if value.isdigit() and 1 <= int(value) <= len(jobs):
            selected_job = jobs[int(value) - 1]
            break
        print(f"1부터 {len(jobs)} 사이의 공고 번호를 입력하거나 0을 입력해주세요.")

    company = selected_job.get("company")
    posting_title = selected_job.get("posting_title")

    if is_duplicate_application(applications, company, posting_title):
        print("이미 지원현황에 등록된 공고입니다.")
        return applications

    print("지원 정보를 입력하세요. 입력하지 않으면 해당 값은 비워둡니다.")
    status = choose_status()
    application_date = ask_date("지원일 (YYYY-MM-DD, 미입력은 Enter): ")
    salary = input("연봉: ").strip() or None
    notes = input("메모: ").strip() or None

    application = {
        "company": company,
        "posting_title": posting_title,
        "job_title": selected_job.get("job_title"),
        "application_status": status,
        "application_date": application_date,
        "document_result_date": None,
        "interview_date": None,
        "final_result_date": None,
        "salary": salary,
        "notes": notes,
        "url": selected_job.get("url")
    }

    applications.append(application)
    if save_applications(applications):
        print("지원내역을 등록했습니다.")
    return applications


def show_applications(applications):
    print("=" * 40)
    print("RE:START 지원현황")
    print("=" * 40)

    if not applications:
        print("등록된 지원내역이 없습니다.")

    for number, application in enumerate(applications, start=1):
        print(f"\n{number}. {application.get('company') or '정보 미확인'}")
        print(f"직무 : {application.get('job_title') or '정보 미확인'}")
        print(f"상태 : {application.get('application_status') or '정보 미확인'}")
        print(f"지원일 : {application.get('application_date') or '-'}")
        print(f"연봉 : {application.get('salary') or '정보 없음'}")
        print(f"메모 : {application.get('notes') or '-'}")

    document_pass_count = sum(
        1 for item in applications if item.get("application_status") == "서류합격"
    )
    interview_count = sum(
        1 for item in applications
        if item.get("application_status") in ["면접예정", "면접완료"]
    )
    final_pass_count = sum(
        1 for item in applications if item.get("application_status") == "최종합격"
    )

    print("\n요약")
    print(f"전체 : {len(applications)}건")
    print(
        "지원예정 : "
        f"{sum(1 for item in applications if item.get('application_status') == '지원예정')}건"
    )
    print(
        "지원완료 : "
        f"{sum(1 for item in applications if item.get('application_status') == '지원완료')}건"
    )
    print(f"서류합격 : {document_pass_count}건")
    print(f"면접진행 : {interview_count}건")
    print(f"최종합격 : {final_pass_count}건")


def choose_application(applications):
    """지원내역을 번호로 보여주고 선택한 항목을 반환합니다."""
    if not applications:
        print("등록된 지원내역이 없습니다.")
        return None

    for number, application in enumerate(applications, start=1):
        company = application.get("company") or "정보 미확인"
        job_title = application.get("job_title") or "정보 미확인"
        status = application.get("application_status") or "정보 미확인"
        print(f"{number}. {company} | {job_title} | {status}")

    index = choose_item(applications, "번호를 선택하세요: ")
    return applications[index]


def change_application_status(applications):
    application = choose_application(applications)
    if application is None:
        return applications

    new_status = choose_status()
    application["application_status"] = new_status

    # 상태에 맞는 날짜를 입력받습니다. 비워두면 해당 날짜는 null입니다.
    date_fields = {
        "지원완료": ("application_date", "지원일"),
        "서류합격": ("document_result_date", "서류 결과일"),
        "서류탈락": ("document_result_date", "서류 결과일"),
        "면접예정": ("interview_date", "면접일"),
        "면접완료": ("interview_date", "면접일"),
        "최종합격": ("final_result_date", "최종 결과일"),
        "최종탈락": ("final_result_date", "최종 결과일")
    }

    if new_status in date_fields:
        field_name, date_label = date_fields[new_status]
        application[field_name] = ask_date(
            f"{date_label} (YYYY-MM-DD, 미입력은 Enter): "
        )

    if save_applications(applications):
        print("지원상태를 변경했습니다.")
    return applications


def edit_application_notes(applications):
    application = choose_application(applications)
    if application is None:
        return applications

    print(f"현재 메모: {application.get('notes') or '-'}")
    new_notes = input("새 메모 (삭제하려면 Enter): ").strip()
    application["notes"] = new_notes or None

    if save_applications(applications):
        print("메모를 수정했습니다.")
    return applications


def main():
    # 프로그램 시작 시 지원현황을 읽습니다. 파일이 없으면 빈 배열로 만듭니다.
    applications = load_json_file(APPLICATIONS_FILE, list, "지원현황")
    if applications is None:
        return

    while True:
        print("\n" + "=" * 40)
        print("RE:START 지원현황 관리")
        print("=" * 40)
        print("1. 지원 등록")
        print("2. 지원현황 보기")
        print("3. 지원상태 변경")
        print("4. 메모 수정")
        print("5. 종료")

        choice = input("선택: ").strip()

        if choice == "1":
            applications = register_application(applications)
        elif choice == "2":
            show_applications(applications)
        elif choice == "3":
            applications = change_application_status(applications)
        elif choice == "4":
            applications = edit_application_notes(applications)
        elif choice == "5":
            print("프로그램을 종료합니다.")
            break
        else:
            print("1부터 5 사이의 번호를 선택해주세요.")


if __name__ == "__main__":
    main()
