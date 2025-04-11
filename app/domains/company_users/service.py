from app.domains.company_users.schemas import CompanyUserRequest
from app.domains.company_users.utils import check_business_number_valid
from app.models import CompanyInfo
from fastapi import HTTPException


# 사업자 등록번호 중복 확인
def check_dupl_business_number(db:Session,business_reg_number : str):
    company_reg_no = db.query(CompanyInfo).filter_by(business_reg_number = business_reg_number).first()
    if company_reg_no:
        raise HTTPException(
            status_code=400,
            detail={"error": "DuplicateBusinessNumber", "message": "이미 등록된 사업자등록번호입니다."}
        )
# 이메일 중복 확인
def check_dupl_email(db:Session,email : str):
    company_user_email = db.query(CompanyUser).filter_by(email= email).first()
    if company_user_email:
        raise HTTPException(
            status_code=400,
            detail={"error": "DuplicateEmail", "message": "이미 가입된 이메일입니다."}
        )

# 회원가입 정보 확인
def register_company_user(db:Session,payload:CompanyUserRequest):
    # 국세청 진위확인 호출
    if not check_business_number_valid(
        payload.business_reg_number,
        payload.opening_date.strftime("%Y%m%d"),
        payload.ceo_name
    ):
        raise HTTPException(
            status_code=400,
            detail={"error": "InvalidBusinessNumber", "message": "유효하지 않은 사업자등록번호입니다."}
        )

    # 중복 체크
    check_dupl_email(db,payload.email)
    check_dupl_business_number(db,payload.business_reg_number)

    # 정보 저장
    company_info = create_company_info(db,payload)
    company_user = create_company_user(db,payload,company_info.id)

    return company_user