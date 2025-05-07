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
    #  시스템 메세지
    system_msg =(
        "당신은 인사(HR)전문 어시스던트 입니다."
        "아래 공고 본문을 정확하게 파악하여 최대 50자 이내의 한두줄로 요약하세요." 
        "반드시 포함할 정보는 직무명, 고용형태, 급여, 근무지, 근무날짜, 근무시간 입니다." 
        "핵심 보조 정보는 우대조건, 학력요구사항, 복리후생 입니다." 
        "명확하고 정확하게 높임말의 문장 형태로 출력하세요." 
        "이모티콘, 추가 설명 일절 금지"
        "예시 : 백엔드 엔지니어를 정규직으로 모집하며 서울 송파구 쿠팡본사에서 근무합니다."
        "연봉 7500만원, 월-금 09시부터 18시 근무이며, 협의불가능합니다."
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
