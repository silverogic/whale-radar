# Phase 1-1: SEC Form 4 수집 및 파싱/필터링 엔진 PoC

## 1. 개요 및 목표
* **목적**: SEC EDGAR 공시 시스템에서 최신 Form 4를 실시간으로 수집하고, 노이즈를 제거하여 경영진의 유의미한 장내 매수(Open Market Purchase, Code P, $100,000 이상) 신호를 선별하는 파이썬 PoC 엔진 구현.
* **핵심 결과물**:
  * SEC EDGAR 최신 Form 4 피드 크롤러 (`sec_client.py`)
  * Form 4 XML 정밀 파서 및 필터링/합산 엔진 (`parser.py`)
  * 통합 실행 및 터미널 출력 CLI (`main.py`)
  * 설정 및 파라미터 모듈 (`config.py`)

---

## 2. 세부 설계 및 규칙

### 2.1 SEC EDGAR 데이터 연동 규칙
* **Endpoint**:
  * SEC EDGAR 최신 공시 RSS Feed:
    `https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=4&company=&dateb=&owner=only&start=0&count=100&output=atom`
  * Form 4 원본 XML 파일 추출 및 다운로드
* **SEC 규정 준수**:
  * `User-Agent` 헤더 필수 적용: `InsiderRadar/1.0 (contact: your_email@domain.com)` 형태
  * Rate Limit: 초당 10회 미만 엄격 제한 (요청 간 지연 시간 0.15초 이상 유지)

### 2.2 필터링 및 집계(Aggregation) 로직
1. **Transaction Code**:
   * 반드시 `P` (Open Market Purchase)만 추출
   * `A` (무상 부여), `M` (옵션 행사), `S` (매도), `G` (증여) 등 제외
2. **거래 금액 집계 (Aggregation)**:
   * 1건의 Form 4 내 여러 행으로 분할 매수한 경우: `sum(shares * price_per_share)`로 동일 공시 내 총 매수액 계산
   * 총 매수액 $\ge$ **$100,000** (설정 파일로 조정 가능)
3. **직책 (Role) 필터링 & 라벨링**:
   * `isOfficer == '1' / 'true'`
   * `isDirector == '1' / 'true'`
   * `isTenPercentOwner == '1' / 'true'` (기관 투자자 가능성 표기)
   * 직책명(`officerTitle`) 추출 (예: CEO, CFO, COO 등)
4. **변동률 계산**:
   * 매수 전 보유 주식 수 및 매수 후 보유 주식 수(`sharesOwnedFollowingTransaction`)를 통한 지분 변동률 계산

---

## 3. 파일 및 디렉토리 구조
```
insider-radar/
├── PLAN.md
├── Phase1-1.md
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── config.py           # 설정 (SEC User-Agent, 필터 임계값)
│   ├── sec_client.py       # SEC Feed 조회 및 파일 다운로드 (Rate-limit 제어)
│   ├── parser.py           # Form 4 XML 파싱, 필터링, 데이터 클래스 정의
│   └── main.py             # 파이프라인 통합 실행 및 CLI 포맷 출력
└── tests/
    └── sample_form4.xml    # 검증용 샘플 Form 4 XML
```

---

## 4. 데이터 모델 (Output Schema)
선별된 내부자 거래 결과 데이터 모델:
```python
@dataclass
class InsiderTrade:
    ticker: str                 # 주식 티커 (예: NVEC, AAPL)
    issuer_name: str            # 기업명
    reporter_name: str          # 내부자 성명
    role: str                   # 직책 (CEO, Director 등)
    is_officer: bool
    is_director: bool
    is_ten_percent: bool
    transaction_date: str       # 거래일자
    shares: float               # 총 매수 주식 수
    avg_price: float            # 가중평균 매수가격
    total_value_usd: float      # 총 매수 금액 ($)
    owned_following: float      # 거래 후 보유 주식 수
    pct_change: Optional[float] # 보유 지분 증가율 (%)
    form4_url: str              # SEC 원문 링크
```

---

## 5. 단계별 구현 및 검증 계획
1. **의존성 설정 (`requirements.txt`)**:
   * `requests`
2. **`config.py`**:
   * 최소 금액($100,000), User-Agent, 엔드포인트 URL 설정
3. **`sec_client.py`**:
   * SEC RSS Atom 피드 파싱 $\rightarrow$ Form 4 공시 메타데이터(Accession Number, CIK, XML 링크) 수집
4. **`parser.py`**:
   * Form 4 XML 파싱 및 Transaction Code `P`, C-Level, \$100k+ 집계 로직 구현
5. **`main.py`**:
   * 전체 파이프라인 구동 및 터미널 요약 출력
6. **실제 SEC 최신 공시 대상 테스트 & 검증**:
   * 파이썬 스크립트 실행하여 실시간 SEC 데이터 필터링 정상 동작 확인
