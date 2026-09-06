# InsiderRadar (인사이더레이더)

> 미국 주식 시장에서 기업 내부자(CEO, CFO, 이사 등)의 장내 직접 매수(Open Market Purchase) 공시(SEC Form 4)를 실시간 감지하여 전달하는 무서버 파이프라인.

---

## 📌 주요 특징
1. **노이즈 100% 제거**: 스톡옵션 행사(Code M), 무상 증여(Code A), 장외 거래 등 주가 시그널과 무관한 공시 필터링.
2. **진짜 매수(Code P)만 선별**: 실제 자기 자본으로 장내 매수한 거래만 포착.
3. **분할 매수 합산(Aggregation)**: 동일 공시 내 여러 날짜/가격으로 쪼개어 매수한 내역을 통합 합산하여 $100,000 이상 여부 판정.
4. **SEC 규정 준수**: User-Agent 정책 및 초당 10회 미만 Rate Limiting(0.15초 대기) 준수.

---

## 🚀 빠른 시작 (Quick Start)

### 1. 패키지 설치
```bash
pip install -r requirements.txt
```

### 2. 테스트 실행
```bash
python -m unittest tests/test_parser.py
```

### 3. 실시간 SEC 공시 스캔 실행
```bash
# 기본 실행 (최신 80건 조회, $100,000 이상 매수 탐지)
python -m src.main

# 옵션 지정 실행 (최근 50건 조회, $50,000 이상 매수 탐지)
python -m src.main --count 50 --min-value 50000
```
