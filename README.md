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

### 3. 실시간 SEC 공시 스캔 & 데이터 갱신
```bash
# 기본 실행 (최신 80건 스캔, $100k+ 매수 감지 및 docs/data/trades.json 자동 업데이트)
python -m src.main

# 옵션 지정 실행 (최근 100건 스캔, $50,000 이상 매수 탐지)
python -m src.main --count 100 --min-value 50000
```

### 4. 로컬 웹 대시보드 미리보기
브라우저에서 `docs/index.html` 파일을 더블클릭하여 바로 열거나, 간단한 로컬 웹 서버를 실행합니다:
```bash
python -m http.server 8000 --directory docs
```
브라우저에서 `http://localhost:8000` 접속 시 초고속 실시간 검색 대시보드를 확인할 수 있습니다.

---

## 🌐 GitHub Pages 무료 웹사이트 배포 방법

1. **GitHub 저장소 생성 및 푸시**:
   ```bash
   git remote add origin https://github.com/<YOUR_USERNAME>/<REPO_NAME>.git
   git branch -M main
   git push -u origin main
   ```
2. **GitHub Pages 활성화 (원클릭)**:
   * GitHub 저장소 페이지 $\rightarrow$ **[Settings]** $\rightarrow$ 좌측 메뉴 **[Pages]** 클릭
   * **Build and deployment** $\rightarrow$ Source를 **`Deploy from a branch`** 선택
   * Branch: **`main`** / Folder: **`/docs`** 선택 후 **[Save]** 클릭
3. **완료!**:
   * 잠시 후 `https://<YOUR_USERNAME>.github.io/<REPO_NAME>/` 링크가 생성되어 전 세계 어디서든 무료로 실시간 검색 대시보드에 접속할 수 있습니다.
   * `.github/workflows/tracker.yml`이 매일 미국 증시 장 마감 후 자동으로 새 공시를 긁어와 웹사이트를 갱신합니다.
