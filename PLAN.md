Project Plan: SEC Form 4 Insider Buying Radar
1. 프로젝트 개요 (Overview)
프로젝트 목적: 미국 주식 시장에서 기업 내부자(CEO, CFO, 이사 등)가 자기 자본으로 직접 장내 매수(Open Market Purchase)한 유의미한 공시(SEC Form 4)를 자동 감지하여 사용자가 등록한 이메일(Email)로 실시간 요약 뉴스레터 전달.
핵심 가치 제안 (Value Proposition):
수천 건의 일일 공시 중 노이즈(스톡옵션 행사, 증여, 소액 매수 등)를 100% 제거하고, 실제 주가 상승 확신을 가진 경영진의 '진짜 매수'만 선별.
별도 서버 비용 없이(0원), 다운타임 리스크 없이 안정적으로 구동되는 무중단 1인 운영 파이프라인.


2. 프로젝트 이름 InsiderRadar (인사이더레이더)
의미: 내부자(Insider)의 매수 신호를 탐지하는 레이더. 직관적이고 기억하기 쉬움.


3. 시스템 아키텍처 (Architecture)
Phase 1: 무서버(Serverless) 단일 채널 검증 구조
스케줄러/실행: GitHub Actions (매일 미국 증시 장 마감 후 또는 장중 30분 간격 실행)
데이터 원천: SEC EDGAR RSS & Submissions API (무료 공공 엔드포인트)
파서/필터: Python 스크립트 (경량 XML 파서 xml.etree.ElementTree / BeautifulSoup)
전송 채널: 사용자 등록 이메일 발송 서비스 (Resend API / Brevo)
비용: 0원 (GitHub Actions 및 Resend/Brevo 무료 티어 활용)
이메일 서비스 무료 티어: Resend(월 3,000건/일 100건), Brevo(일 300건/월 약 9,000건) 무료 제공. 초기 구독자 50~100명 규모에서 추가 비용 0원.

[GitHub Actions (Cron Trigger)]

         │ (1) SEC EDGAR 최신 Form 4 조회

         ▼

[Python Filter Engine]

  • Transaction Code == 'P' (Open Market Purchase)

  • Total Value >= $100,000

  • Officer / Director == True

         │ (2) 유효한 건 필터링 & 메시지 포맷팅

         ▼

[Email Dispatch Service (Resend/Brevo API)]

         │ (3) sendEmail (To: Subscriber DB/Sheets)

         ▼

[사용자 등록 이메일 인박스 (HTML 뉴스레터)]
Phase 2: 웹 대시보드 및 1:1 맞춤형 봇 확장 (수요 검증 후)
데이터베이스: Supabase (무료 PostgreSQL)에 감지된 내역 및 유저 관심종목 적재
조회 웹 대시보드: Koyeb 무료 인스턴스에 읽기 전용 FastAPI + Streamlit/Next.js 서빙
1:1 개인화 봇: 유저별 /watch <TICKER> 등록 및 유료 구독 관리


4. 데이터 필터링 규칙 (Filter Rules)
항목
필터 조건
제외 대상 (노이즈)
Transaction Code
P (Open Market Purchase)
A (무상 증여), M (스톡옵션 행사), S (매도), G (기부) 등
최소 거래 금액
건당 또는 당일 누적 $100,000 이상
$10,000 미만 소액 의무 매입 등
직책 (Role)
CEO, CFO, COO, Director, 10% Owner
일반 직원, 하위 관리자
중복 방지
최근 24시간 내 발송된 AccessionNumber 캐싱
중복 알림 방지



5. 이메일 알림 포맷 (Email Template)
[Subject] 🟢 [Insider Radar] 오늘의 경영진 장내매수 알림: NVEC 외 N건
[Body - HTML 뉴스레터]
━━━━━━━━━━━━━━━━━━

• 매수자: Daniel A. Baker (CEO)

• 매수 규모: 2,500주 ($205,000 / 약 2.7억 원)

• 평균 매수가: $82.00

• 보유 지분 변동: 142,000주 ➡️ 144,500주 (+1.76%)

━━━━━━━━━━━━━━━━━━

🔗 [SEC Form 4 원문 보기](https://www.sec.gov/...)


6. 단계별 실행 마일스톤 (Actionable Milestones)
[Milestone 1] 파이썬 파이프라인 PoC 작성 (1~2일차)
SEC EDGAR API 헤더 규칙(User-Agent: SampleApp user@email.com) 준수 엔드포인트 연동
당일 제출된 Form 4 XML 다운로드 및 필터링 로직 구현 (Code 'P', $100k+, C-Level)
로컬 터미널에서 당일 대상 종목 3~5건 정상 출력 확인
[Milestone 2] 이메일 등록 폼 연동 및 발송 자동화 (3~4일차)
Tally/Google Sheets를 이용한 사용자 이메일 구독 폼 및 DB 구축
GitHub 리포지토리 생성 및 파이썬 코드 푸시
.github/workflows/monitor.yml 작성 (정기 Cron 스케줄 설정)
GitHub Secrets에 RESEND_API_KEY 등록 및 Resend API 기반 이메일 템플릿 발송 테스트
[Milestone 3] 채널 오픈 및 1차 수요 검증 (5~7일차)
투자 커뮤니티, 블로그, SNS 등에 채널 링크 공유
1~2주간 자동 운영하며 파싱 에러, 누락 케이스 모니터링
구독자 50~100명 확보 시 1:1 봇 및 웹 대시보드(Koyeb/Supabase) 개발 착수


7. 리스크 및 제약 관리 (Cost & Constraints)
SEC Rate Limit: 초당 10회 제한 엄격 준수 (time.sleep(0.15) 적용).
GitHub Actions 무료 한도 관리: 1회 실행 시간을 30초 이내로 최적화하여 일 24회 실행 기준 월 약 360분 소모 (월 2,000분 무료 한도의 18% 수준).
운영 부담 Zero: 다운타임 발생 시 GitHub Actions가 자동 재시도 및 실패 메일 알림 제공.

