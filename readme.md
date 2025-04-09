# 🧓 Senior Job Platform

시니어 세대를 위한 **맞춤형 일자리 플랫폼**  
구직자는 이력서를 작성하고 채용 공고에 지원할 수 있으며, 기업 회원은 공고를 등록하고 인재를 모집할 수 있는 채용 서비스입니다.

---

## ⚙️ 기술 스택

### 🔹 Frontend
- React
- React Router
- React Hook Form
- Zustand
- Axios
- SASS / SCSS
- React Icons
- Vite
- Alias 경로 설정

### 🔸 Backend
- FastAPI
- PostgreSQL
- Swagger (자동 API 문서 생성)
- Logging (각 모델 단위)
- .env 환경변수 설정
- CI/CD: black, isort, modeltest, viewstest

---

## 📁 프로젝트 구조 및 규칙

- **Server Deployment 담당**: 박철민
- **Pull Requests**: 최소 1명 이상의 승인 후 Merge
- **CI/CD**: PR 시 자동 린팅 및 테스트 수행
- **환경 변수**: `.env` 파일 사용 (`VITE_API_URL` 등)
- **Swagger**: `/docs` 경로로 자동 문서 제공
  - 자동 생성되지 않는 내용은 프론트와 협의하여 문서화

---

## 🧑‍💻 팀 소개

| 역할 | 이름 |
|------|------|
| **BE** (Backend) | 박철민, 신혜지, 문선홍, 이영우 |
| **FE** (Frontend) | 임태영, 서혜진, 박현정, 이희정 |

---

## 🧩 핵심 기능 요약

### 👤 회원가입
- 구직자: 관심 분야, 유입 경로 등 선택 포함
- 기업회원: 사업자등록번호, 담당자 정보 등 입력
- 유효성 검사 및 중복 확인 기능 제공

### 📝 공고 등록
- 기업 및 어드민만 작성 가능
- 모든 필드 단일 텍스트 / 직종은 드롭다운
- 약관 동의 필수 체크

### 🔍 공고 탐색
- 키워드 기반 실시간 검색
- 직군, 지역, 요약 내용 포함 검색
- 상세 페이지에서 이력서 기반 간편 지원

### 📄 이력서 관리
- 기본 정보 + 경력 + 학력 + 자기소개
- 경력 반복 추가 기능
- 저장 시 즉시 반영

### 🏠 마이페이지
- 구직자: 관심공고/추천공고/이력서 관리
- 기업회원: 기업 정보 수정, 등록 공고 관리

---

## 📄 API 문서 (Swagger)

- FastAPI 기반 `/docs` 자동 생성
- 자동 생성이 어려운 항목은 협의를 통해 수동 작성 예정

---

## ✅ 사용 방법 (예시)

```bash
# .env 설정
VITE_API_URL=https://api.example.com

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
