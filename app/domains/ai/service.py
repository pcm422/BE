from app.core.clova_utils import call_clova_summary
from app.domains.ai.schemas import AIJobPostSchema


def format_job_for_summary(job: AIJobPostSchema) -> str:
    parts = [f"제목: {job.title}"]
    if job.job_category: parts.append(f"직무 분야: {job.job_category}")
    if job.education:    parts.append(f"요구학력: {job.education}")
    if job.employment_type:
        parts.append(f"고용 형태: {job.employment_type}")
    if job.salary:
        parts.append(f"급여: {job.payment_method} {job.salary:,}원")
    if job.work_duration:
        parts.append(f"근무기간: {job.work_duration}")
    if job.work_days:
        day_nego = "협의가능" if job.is_work_days_negotiable else "협의불가능"
        parts.append(f"근무 날짜: {job.work_days} ({day_nego})")
        if job.work_start_time and job.work_end_time:
            time_nego = "협의가능" if job.is_work_time_negotiable else "협의불가능"
            parts.append(f"{job.work_start_time} {job.work_end_time} ({time_nego})")
    if job.career:
        parts.append(f"경력: {job.career}")
    if job.work_place_name:
        parts.append(f"근무지: {job.work_place_name} ({job.work_address})")
    if job.benefits:
        parts.append(f"복지: {job.benefits}")
    if job.preferred_conditions:
        parts.append(f"우대 조건: {job.preferred_conditions}")
    if job.description:
        parts.append(f"설명: {job.description}")
    return "\n".join(parts)

async def summary_jobposting(job: AIJobPostSchema) -> str:
    content = format_job_for_summary(job)
    print(content)
    system_msg = (
        "당신은 인사(HR) 전문 어시스턴트입니다. "
        "아래 공고 정보를 보고, 자연스럽고 공식적인 한국어 문장으로 최대 50자 이내의 한두 문장으로 요약하세요. "
        "요약문에 반드시 포함할 정보: 회사 이름, 직무명, 경력 요구 수준, 고용 형태, 연봉, 근무지, 모집 기간, 근무 요일, 근무 시간. "
        "우대조건, 복리후생은 선택적으로 포함할 수 있지만, 문장이 너무 길어지지 않도록 주의하세요. "
        "출력 규칙: "
        "1) “회사이름에서”로 시작하는 한두 문장으로 작성합니다. "
        "2) 괄호, 대괄호, 슬래시(/), 쉼표 나열 형식, 따옴표, 기타 모든 기호 사용을 금지합니다. "
        "3) 입력 텍스트에 포함된 분류 태그(예: [뷰티,코스메틱])는 출력에서 제거하고 절대 포함하지 않습니다. "
        "4) 서두나 맺음말 없이 오직 요약문만 출력합니다. "
        "5) 문장은 반드시 마침표로 끝맺습니다. "
        "예시1: 쿠팡 본사에서 파이썬 백엔드 엔지니어를 정규직 연봉 7,500만 원에 모집하며 서울 송파구에서 근무합니다. "
        "예시2: 삼성전자에서 데이터 엔지니어를 계약직 연봉 6,000만 원으로 채용하며 경기도 수원시에서 근무합니다."
    )
    # 유저 메세지
    user_msg = f"공고내용 :\n{content}"

    # payload 구성
    messages =[
        {"role":"system", "content":system_msg},
        {"role":"user", "content":user_msg},
    ]

    # 호출하기
    return await call_clova_summary(messages)
