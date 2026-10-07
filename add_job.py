import json
import re
from pathlib import Path


# jobs.json은 현재 프로그램 파일(add_job.py)과 같은 폴더에 저장합니다.
jobs_file_path = Path(__file__).with_name("jobs.json")


# 기존 공고를 먼저 읽어, 파일이 잘못된 경우 입력이나 저장을 진행하지 않습니다.
if jobs_file_path.exists():
    try:
        with open(jobs_file_path, "r", encoding="utf-8") as file:
            jobs = json.load(file)
    except json.JSONDecodeError as error:
        print(
            "오류: jobs.json의 JSON 형식이 올바르지 않습니다. "
            f"{error.lineno}번째 줄의 쉼표나 따옴표를 확인해주세요."
        )
        raise SystemExit(1)
    except OSError as error:
        print(f"오류: jobs.json 파일을 읽을 수 없습니다. {error}")
        raise SystemExit(1)

    if not isinstance(jobs, list):
        print("오류: jobs.json의 최상위 구조는 공고 목록 배열([])이어야 합니다.")
        raise SystemExit(1)
else:
    # 파일이 아직 없으면 새 공고를 담을 빈 목록으로 시작합니다.
    jobs = []


def get_optional_text(prompt):
    """입력값을 다듬고, 빈 입력은 JSON null로 저장하도록 None을 반환합니다."""
    value = input(prompt).strip()
    if value == "":
        return None
    return value


def get_experience_months(prompt):
    """경력연수를 입력받아 개월로 변환합니다. 빈 입력은 None입니다."""
    while True:
        value = input(prompt).strip()

        if value == "":
            return None

        try:
            years = int(value)
        except ValueError:
            print("0 이상의 정수로 입력해주세요. 예: 10")
            continue

        if years < 0:
            print("경력연수는 0 이상으로 입력해주세요.")
            continue

        return years * 12


JOB_FIELDS = [
    ("company", "회사명"),
    ("posting_title", "공고명"),
    ("job_title", "직무명"),
    ("main_tasks", "주요업무"),
    ("required_experience_min_months", "최소 요구경력"),
    ("required_experience_max_months", "최대 요구경력"),
    ("location", "근무지역"),
    ("work_type", "출근방식"),
    ("employment_type", "고용형태"),
    ("revenue", "회사 매출액"),
    ("revenue_trend", "최근 매출 추이"),
    ("operating_profit", "영업이익"),
    ("operating_margin", "영업이익률"),
    ("operating_profit_trend", "최근 영업이익 추이"),
    ("required_qualifications", "필수자격"),
    ("preferred_qualifications", "우대사항"),
    ("education", "학력"),
    ("url", "공고 URL")
]

# 공고에서 자주 쓰이는 라벨만 대응합니다. 모르는 라벨은 추측하지 않습니다.
LABELS = {
    "회사명": "company", "기업명": "company",
    "공고명": "posting_title", "채용공고명": "posting_title", "제목": "posting_title",
    "직무명": "job_title", "모집직무": "job_title", "모집부문": "job_title", "직무": "job_title",
    "주요업무": "main_tasks", "담당업무": "main_tasks", "업무내용": "main_tasks", "직무내용": "main_tasks",
    "경력": "experience", "경력조건": "experience", "필수경력": "experience",
    "최소요구경력": "experience", "근무지역": "location", "근무지": "location",
    "출근방식": "work_type", "근무방식": "work_type", "출근형태": "work_type",
    "고용형태": "employment_type", "고용조건": "employment_type",
    "회사매출액": "revenue", "매출액": "revenue", "최근매출추이": "revenue_trend", "매출추이": "revenue_trend",
    "영업이익": "operating_profit", "영업이익률": "operating_margin",
    "최근영업이익추이": "operating_profit_trend", "영업이익추이": "operating_profit_trend",
    "필수자격": "required_qualifications", "자격요건": "required_qualifications", "지원자격": "required_qualifications",
    "우대사항": "preferred_qualifications", "우대조건": "preferred_qualifications",
    "학력": "education", "학력요건": "education", "공고URL": "url", "URL": "url"
}


def normalize_label(value):
    """라벨에 붙은 공백, 괄호, 글머리 기호를 제거합니다."""
    return re.sub(r"[\s\[\](){}*•·-]", "", value).lower()


def read_pasted_text():
    """END가 단독으로 입력될 때까지 여러 줄의 공고를 받습니다."""
    print("채용공고 내용을 붙여넣으세요.")
    print("입력이 끝나면 마지막 줄에 END를 입력하세요.")
    lines = []

    while True:
        try:
            line = input()
        except EOFError:
            break

        if line.strip().upper() == "END":
            break
        lines.append(line)

    return "\n".join(lines)


def extract_experience_months(text):
    """명시적인 N년 이상/이하 또는 연차 범위만 개월로 변환합니다."""
    range_match = re.search(
        r"(\d+)\s*년\s*(?:이상\s*)?(?:~|∼|～|-)\s*(\d+)\s*년(?:\s*이하)?",
        text
    )
    if range_match:
        minimum_years = int(range_match.group(1))
        maximum_years = int(range_match.group(2))
        if minimum_years <= maximum_years:
            return minimum_years * 12, maximum_years * 12
        return None, None

    minimum_match = re.search(r"(\d+)\s*년\s*이상", text)
    maximum_match = re.search(r"(\d+)\s*년\s*이하", text)
    minimum_months = int(minimum_match.group(1)) * 12 if minimum_match else None
    maximum_months = int(maximum_match.group(1)) * 12 if maximum_match else None
    return minimum_months, maximum_months


def extract_job_fields(text):
    """라벨이 분명한 공고 정보만 임시 추출하고 나머지는 None으로 둡니다."""
    sections = {}
    current_field = None

    for line in text.splitlines():
        stripped_line = line.strip()
        if not stripped_line:
            continue

        if ":" in stripped_line or "：" in stripped_line:
            separator = ":" if ":" in stripped_line else "："
            label, value = stripped_line.split(separator, 1)
            normalized_label = normalize_label(label)
            current_field = LABELS.get(normalized_label)
            if current_field is not None and value.strip():
                sections.setdefault(current_field, []).append(value.strip())
            continue

        normalized_line = normalize_label(stripped_line)
        if normalized_line in LABELS:
            current_field = LABELS[normalized_line]
            continue

        if current_field is not None:
            sections.setdefault(current_field, []).append(stripped_line)

    extracted = {field: None for field, label in JOB_FIELDS}

    for field, values in sections.items():
        if field not in extracted:
            continue
        value = "\n".join(values).strip()
        if value:
            extracted[field] = value

    experience_text = "\n".join(
        sections.get("experience", []) + sections.get("required_qualifications", [])
    )
    if not experience_text:
        experience_text = text
    minimum_months, maximum_months = extract_experience_months(experience_text)
    extracted["required_experience_min_months"] = minimum_months
    extracted["required_experience_max_months"] = maximum_months

    # URL은 명시적인 웹 주소 형태가 있을 때만 저장합니다.
    if extracted["url"] is None:
        url_match = re.search(r"https?://[^\s<>\]\[()]+", text)
        if url_match:
            extracted["url"] = url_match.group(0).rstrip(".,")

    return extracted


def make_job_record(fields):
    """추출 또는 입력한 값을 jobs.json에서 사용하는 공고 구조로 만듭니다."""
    job = {field: fields.get(field) for field, label in JOB_FIELDS}
    job.update({
        "required_experience_is_mandatory": None,
        "location_score": None,
        "revenue_score": None,
        "operating_profit_score": None,
        "exclusion_reason": None
    })
    return job


def input_direct_fields():
    """기존 방식대로 공고 항목을 하나씩 입력받습니다."""
    print("새 채용공고 정보를 입력해주세요. 입력하지 않고 Enter를 누르면 null로 저장됩니다.")
    fields = {}

    for field, label in JOB_FIELDS:
        if field == "required_experience_min_months":
            fields[field] = get_experience_months("5. 최소 요구경력(년, 예: 10): ")
        elif field == "required_experience_max_months":
            fields[field] = get_experience_months("6. 최대 요구경력(년, 예: 17): ")
        else:
            number = JOB_FIELDS.index((field, label)) + 1
            fields[field] = get_optional_text(f"{number}. {label}: ")

    return make_job_record(fields)


def display_job(job, title):
    """저장 전에 공고의 전체 입력값을 보여줍니다."""
    print("\n" + "=" * 40)
    print(title)
    print("=" * 40)

    for field, label in JOB_FIELDS:
        value = job.get(field)
        if field in ["required_experience_min_months", "required_experience_max_months"]:
            if value is None:
                shown_value = "null"
            else:
                shown_value = f"{value}개월"
        else:
            shown_value = value if value is not None else "null"
        print(f"{label}: {shown_value}")


def edit_extracted_job(job):
    """Enter는 추출값 유지, 새 입력은 해당 항목을 수정합니다."""
    edited_job = dict(job)

    for field, label in JOB_FIELDS:
        current = edited_job.get(field)
        if field in ["required_experience_min_months", "required_experience_max_months"]:
            current_text = "null" if current is None else f"{current}개월"
            value = input(f"{label} (현재 {current_text}, 년 단위 입력): ").strip()
            if value == "":
                continue
            try:
                years = int(value)
                if years < 0:
                    raise ValueError
            except ValueError:
                print("0 이상의 정수 연수로 입력해주세요. 기존 값을 유지합니다.")
                continue
            edited_job[field] = years * 12
        else:
            current_text = current if current is not None else "null"
            value = input(f"{label} (현재 {current_text}): ").strip()
            if value:
                edited_job[field] = value

    return edited_job


def is_duplicate(job):
    """회사명과 공고명이 모두 같은 공고가 있는지 확인합니다."""
    company = job.get("company")
    posting_title = job.get("posting_title")
    if company is None or posting_title is None:
        return False

    for existing_job in jobs:
        if not isinstance(existing_job, dict):
            print("오류: jobs.json의 공고 항목은 JSON 객체({})여야 합니다.")
            raise SystemExit(1)
        if (
            existing_job.get("company") == company
            and existing_job.get("posting_title") == posting_title
        ):
            return True

    return False


def save_job(job):
    """중복을 확인한 뒤 기존 공고 배열의 마지막에 새 공고를 저장합니다."""
    if is_duplicate(job):
        print("이미 등록된 공고입니다.")
        return

    jobs.append(job)
    try:
        with open(jobs_file_path, "w", encoding="utf-8") as file:
            json.dump(jobs, file, ensure_ascii=False, indent=2)
            file.write("\n")
    except OSError as error:
        # 저장 실패 시 메모리 목록에서도 추가된 항목을 되돌립니다.
        jobs.pop()
        print(f"오류: jobs.json에 저장할 수 없습니다. {error}")
        raise SystemExit(1)

    print("채용공고가 jobs.json에 추가되었습니다.")
    print("python main.py를 실행하면 평가할 수 있습니다.")


def run_paste_flow():
    """붙여넣은 공고를 추출하고 사용자가 확인한 뒤 저장합니다."""
    pasted_text = read_pasted_text()
    job = make_job_record(extract_job_fields(pasted_text))
    display_job(job, "자동 추출 결과")

    print("\n추출 결과를 확인하세요.")
    print("1. 그대로 저장")
    print("2. 수정 후 저장")
    print("3. 취소")
    choice = input("선택: ").strip()

    if choice == "1":
        save_job(job)
    elif choice == "2":
        job = edit_extracted_job(job)
        display_job(job, "수정한 공고 정보")
        save_job(job)
    else:
        print("저장하지 않았습니다.")


def run_direct_flow():
    """기존 직접 입력과 저장 전 확인 절차를 유지합니다."""
    job = input_direct_fields()
    display_job(job, "입력 내용을 확인해주세요.")
    confirmation = input("\n저장하시겠습니까? (y/n) ").strip().lower()

    if confirmation == "y":
        save_job(job)
    else:
        print("저장하지 않았습니다.")


print("=" * 40)
print("RE:START 채용공고 등록")
print("=" * 40)
print("1. 직접 입력")
print("2. 채용공고 텍스트 붙여넣기")
method = input("등록 방법을 선택하세요: ").strip()

if method == "1":
    run_direct_flow()
elif method == "2":
    run_paste_flow()
else:
    print("1 또는 2를 선택해주세요.")
