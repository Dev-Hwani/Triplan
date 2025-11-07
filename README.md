# 🌍 Triplan – AI Chatbot 기반 여행 플래너 웹 서비스

---

## 🔍 프로젝트 간단 설명
AI Chatbot과 Open API를 활용하여 사용자가 여행 일정을 작성하면 맞춤형 여행 일정을 자동으로 추천하는 웹 서비스입니다.  
사용자가 목적지와 여행 조건을 입력하면 Chatbot이 최적화된 일정과 추천 장소를 실시간으로 제공합니다.  

---

## 🎯 프로젝트 목적
- 대학교 직업훈련 과정에서 습득한 Python, Django, Database 기술을 실제 팀 프로젝트에 적용  
- 실제 웹 서비스 개발 경험과 팀 협업 능력 향상 
- 여행자들이 쉽게 일정을 작성하고, 맞춤형 관광지 추천을 받을 수 있는 서비스 구현

---

## 👥 인력 구성
- 총 4명 (팀 프로젝트)  
  - TL: 1명  
  - Backend: 2명  
  - Frontend: 1명  

---

## ⚙️ 주요 기능
1. **회원 관리**
   - 회원가입, 로그인, 로그아웃
   - 비밀번호 해싱 및 계정 활성화 관리
2. **여행 일정 CRUD**
   - 일정 생성, 수정, 삭제, 조회
   - DAY별 세부 일정 관리
   - 일정 이미지 업로드 및 지역 기반 검색
3. **관광지 정보 관리**
   - 관광지명, 주소, 이미지 관리
   - 조회수, 찜 수 통계 관리
4. **커뮤니티 기능**
   - 게시글 작성/수정/삭제
   - 댓글/대댓글 작성
   - 좋아요/북마크 기능 (중복 방지)
5. **AI 기반 Chatbot**
   - OpenAI GPT-4o-mini 모델 사용
   - 사용자 입력 기반 맞춤 일정 생성
6. **추천 장소 API 연동**
   - Google Places API, 한국관광공사 API
   - 실시간 추천 관광지 제공

---

## 🛠 기술 스택
- Frontend: HTML, CSS, JavaScript  
- Backend: Python, Django, REST API, Open API (Google Maps API, 한국관광공사 API)  
- Database: MySQL  
- 개발 환경: Windows, PyCharm, Git, GitHub  

---

## 💼 담당 역할 (Back-End)

### Database 최적화
- ERD 분석 단계에서 PK/FK 설계 미흡, 인덱스 부재, 불필요한 관계 발견  
- 테이블 간 관계 재설정 및 PK/FK 기반 정규화 수행 → 데이터 참조 무결성 확보  
- 검색 빈도 높은 필드에 인덱스 적용 → 쿼리 응답 속도 75ms → 10ms (약 85% 개선)
- Debug Toolbar, MySQL EXPLAIN 활용하여 쿼리 성능 검증 및 최적화

### API 설계 및 구현
- 사용자가 입력한 목적지와 여행 조건에 맞춰 맞춤형 관광지 추천 기능 개발
- Open API(Google Maps API, 한국관광공사 API)를 활용하여 RESTful API 설계 및 Django API 엔드포인트 구축  
- Google Maps API 및 한국관광공사 API 연동 → 데이터 커버리지 **65% → 92%**
- 추천 적중률 **35% → 78%**, 검색 정확도 **70% → 90% (+20%p)** 향상
- Django API 예외 처리 및 로그 기록 적용 → 안정적 서비스 운영 

### AI 기반 Chatbot 개발
- OpenAI GPT-4o-mini 모델 활용 → 여행 플래너 특화 Chatbot 개발
- 시스템 프롬프트 최적화 → 추천 정확도 **60% → 92%**  
- HTML/JSON 출력 구조화 → UI 표시 효율 40% 개선, UI 가독성 85% 향상  

---

## 🧾 ERD(Entity Relationship Diagram)
<img width="1341" height="1191" alt="image" src="https://github.com/user-attachments/assets/ed6c5fc6-ca4a-4fb2-9614-768b6b2dd713" />

---

## 🖼️ Prototype
<img width="1602" height="883" alt="image" src="https://github.com/user-attachments/assets/20755e99-4d80-48e0-a405-2e059cc37602" />

---

## 📈 Flow Chart
<img width="977" height="473" alt="image" src="https://github.com/user-attachments/assets/853d10d5-e4c6-4aa4-85c5-82292a29b881" />

---
