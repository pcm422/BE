import pytest
from pydantic import ValidationError
from datetime import date, timedelta, datetime

# 테스트 대상 스키마 및 Enum 임포트
from app.domains.job_postings.schemas import (
    JobPostingCreate,
    JobPostingUpdate,
    JobPostingResponse # 응답 스키마 추가
)
from app.models.job_postings import (
    EducationEnum,
    PaymentMethodEnum,
    JobCategoryEnum,
    WorkDurationEnum,
)

# --- 테스트 데이터 생성 헬퍼 ---
def get_base_create_data(**overrides) -> dict:
    """JobPostingCreate에 필요한 모든 필수/기본 필드를 포함한 딕셔너리 반환"""
    data = {
        "title": "기본 테스트 공고",
        "recruit_period_start": date.today(),
        "recruit_period_end": date.today() + timedelta(days=30),
        "is_always_recruiting": False,
        "education": EducationEnum.college_4,
        "recruit_number": 1,
        "benefits": "4대보험, 스톡옵션",
        "preferred_conditions": "테스트 코드 작성",
        "other_conditions": "긍정적인 태도",
        "work_address": "서울시 테스트구 테스트동",
        "work_place_name": "테스트 베이스 주식회사",
        "payment_method": PaymentMethodEnum.yearly,
        "job_category": JobCategoryEnum.it,
        "work_duration": WorkDurationEnum.more_1_year,
        "is_work_duration_negotiable": False,
        "career": "3년 이상",
        "employment_type": "정규직",
        "salary": 60000000,
        "work_days": "주 5일(월~금)",
        "is_work_days_negotiable": False,
        "is_schedule_based": False,
        "work_start_time": "09:30",
        "work_end_time": "18:30",
        "is_work_time_negotiable": False,
        "description": "상세 설명입니다.",
        "summary": "요약글입니다.",
        "latitude": 37.5665,
        "longitude": 126.9780,
    }
    data.update(overrides)
    return data

# --- JobPostingCreate 스키마 테스트 ---

def test_job_posting_create_valid():
    """유효한 데이터로 JobPostingCreate 스키마 생성 성공 테스트"""
    valid_data = get_base_create_data()
    try:
        schema = JobPostingCreate(**valid_data)
        # 주요 필드 값 확인
        assert schema.title == valid_data["title"]
        assert schema.salary == valid_data["salary"]
        assert schema.education == EducationEnum.college_4
    except ValidationError as e:
        pytest.fail(f"유효한 데이터로 생성 실패: {e}")

def test_job_posting_create_missing_required_field():
    """필수 필드 누락 시 ValidationError 발생 테스트"""
    invalid_data = get_base_create_data()
    del invalid_data["title"] # 필수 필드 'title' 제거
    with pytest.raises(ValidationError) as excinfo:
        JobPostingCreate(**invalid_data)
    # 'title' 필드가 누락되었다는 에러 확인
    assert any(err['loc'] == ('title',) and 'Field required' in err['msg'] for err in excinfo.value.errors())

def test_job_posting_create_invalid_type():
    """잘못된 타입의 데이터 입력 시 ValidationError 발생 테스트"""
    invalid_data = get_base_create_data(salary="육천만원") # int여야 하는데 str 입력
    with pytest.raises(ValidationError) as excinfo:
        JobPostingCreate(**invalid_data)
    # 'salary' 필드에서 타입 에러 발생 확인
    assert any(err['loc'] == ('salary',) and 'Input should be a valid integer' in err['msg'] for err in excinfo.value.errors())

def test_job_posting_create_invalid_enum():
    """잘못된 Enum 값 입력 시 ValidationError 발생 테스트"""
    invalid_data = get_base_create_data(education="중졸") # EducationEnum에 없는 값
    with pytest.raises(ValidationError) as excinfo:
        JobPostingCreate(**invalid_data)
    # 'education' 필드에서 enum 값 에러 발생 확인
    assert any(err['loc'] == ('education',) and 'Input should be' in err['msg'] for err in excinfo.value.errors())

def test_job_posting_create_validator_negative_salary():
    """급여 필드 validator 테스트 (음수 입력 시 ValidationError)"""
    # 이 테스트는 salary 필드에 음수 값을 허용하지 않는 validator가 있다고 가정
    invalid_data = get_base_create_data(salary=-1000000)
    with pytest.raises(ValidationError) as excinfo:
        JobPostingCreate(**invalid_data)
    # salary 필드 관련 에러 메시지 확인 (validator 구현에 따라 메시지 내용 달라짐)
    assert any(err['loc'] == ('salary',) for err in excinfo.value.errors())
    # 예: assert "must be greater than zero" in str(excinfo.value)

def test_job_posting_create_validator_recruitment_dates():
    """모집 기간 날짜 validator 테스트 (시작일 > 종료일 시 ValidationError)"""
    invalid_data = get_base_create_data(
        recruit_period_start=date.today() + timedelta(days=1),
        recruit_period_end=date.today(),
        is_always_recruiting=False
    )
    with pytest.raises(ValidationError) as excinfo:
        JobPostingCreate(**invalid_data)
    # 모델 레벨 validator 에러 메시지 확인
    assert "모집 시작일은 종료일보다 빨라야 합니다" in str(excinfo.value)


# --- JobPostingUpdate 스키마 테스트 ---

def test_job_posting_update_valid_empty():
    """빈 데이터로 JobPostingUpdate 생성 성공 테스트"""
    try:
        JobPostingUpdate()
    except ValidationError as e:
        pytest.fail(f"빈 dict로 JobPostingUpdate 생성 실패: {e}")

def test_job_posting_update_valid_partial():
    """일부 데이터만으로 JobPostingUpdate 생성 성공 테스트"""
    update_data = {"title": "수정된 공고 제목", "salary": 65000000}
    try:
        schema = JobPostingUpdate(**update_data)
        assert schema.title == update_data["title"]
        assert schema.salary == update_data["salary"]
        assert schema.description is None # 업데이트 안 된 필드는 None
    except ValidationError as e:
        pytest.fail(f"일부 데이터로 업데이트 실패: {e}")

def test_job_posting_update_invalid_type():
    """업데이트 시 잘못된 타입 데이터 입력 ValidationError 테스트"""
    update_data = {"salary": "육천오백"} # int여야 함
    with pytest.raises(ValidationError) as excinfo:
        JobPostingUpdate(**update_data)
    assert any(err['loc'] == ('salary',) for err in excinfo.value.errors())

def test_job_posting_update_validator_recruitment_dates():
    """업데이트 시 모집 기간 날짜 validator 테스트"""
    update_data = {
        "recruit_period_start": date.today() + timedelta(days=1),
        "recruit_period_end": date.today(),
        "is_always_recruiting": False
    }
    with pytest.raises(ValidationError) as excinfo:
        JobPostingUpdate(**update_data)
    assert "모집 시작일은 종료일보다 빨라야 합니다" in str(excinfo.value)

# --- JobPostingResponse 스키마 테스트 ---

def test_job_posting_response_valid():
    """JobPostingResponse 스키마 생성 성공 테스트"""
    response_data = {
        "id": 123,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        # get_base_create_data의 필드들을 포함한다고 가정
        **get_base_create_data(title="응답 스키마 테스트 공고"),
        # *** 누락되었던 필드 추가 ***
        "author_id": 1, # 예시 ID
        "company_id": 1, # 예시 ID
        # Response 스키마에만 추가된 필드 (예시)
        "is_favorited": False,
    }
    try:
        schema = JobPostingResponse(**response_data)
        assert schema.id == 123
        assert schema.title == "응답 스키마 테스트 공고"
        assert schema.author_id == 1
        assert schema.company_id == 1
        assert schema.is_favorited is False
    except ValidationError as e:
        pytest.fail(f"JobPostingResponse 생성 실패: {e}")
