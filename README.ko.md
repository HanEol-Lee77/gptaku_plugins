[English](README.md) | 한국어

# gptaku-plugins

> **AI Native가 되고 싶은 사람들을 위한 Claude Code 플러그인 마켓플레이스.**

AI Native란 AI를 단순히 도구로 쓰는 게 아니라, 기획부터 실행까지 AI를 자연스럽게 녹여내는 것입니다. 연습이 필요하고, 배우는 사람들을 위한 도구가 필요합니다. 이 플러그인들은 그 과정에서 만나는 구체적인 벽을 하나씩 허물기 위해 만들어졌습니다.

[빠른 시작](#빠른-시작) • [플러그인](#사용-가능한-플러그인) • [왜 만들었나?](#왜-이-플러그인들인가) • [요구사항](#요구사항)

---

## 빠른 시작

### 1. 마켓플레이스 등록 (처음 한 번만)

```
/plugin marketplace add https://github.com/fivetaku/gptaku_plugins.git
```

### 2. 플러그인 설치

```
/plugin install
```

목록에서 고르거나, 이름으로 바로 설치:

```
/plugin install show-me-the-prd
```

> **한 번에 하나씩**만 설치됩니다. 여러 개 필요하면 명령을 반복하세요.

### 3. Claude Code 재시작

설치/업데이트 후 플러그인 활성화를 위해 Claude Code를 재시작합니다.

### 4. 업데이트

```
/plugin update
```

---

## 왜 이 플러그인들인가

- **배우는 사람을 위해** — Git을 모르면 `git-teacher`가 클라우드 서비스 비유로 설명, PRD를 못 쓰면 `show-me-the-prd`가 인터뷰로 만들어줌
- **API 키 없음, 가입 없음** — 설치 즉시 동작. 개발자 포털 등록도, OAuth도, 환경변수도 없음
- **기능이 아니라 결과 중심** — 각 플러그인이 구체적인 벽(차단 사이트, 백지 PRD, 병렬 코딩, 딥리서치)을 해결. 범용 툴킷이 아님
- **한글 우선, 영문 지원** — 한글로 만들어지고, 모든 플러그인은 이중언어 문서 제공
- **조합 가능** — 플러그인끼리 충돌 없음. 필요한 것만 설치하고 나머지는 무시

---

## 사용 가능한 플러그인

| 플러그인 | 설명 |
|---------|------|
| [docs-guide](https://github.com/fivetaku/docs-guide) | 공식문서 기반 정확한 답변 — llms.txt 표준 + 68개+ 라이브러리 |
| [git-teacher](https://github.com/fivetaku/git-teacher) | 비개발자를 위한 Git/GitHub 온보딩 — 클라우드 비유로 5단계 |
| [vibe-sunsang](https://github.com/fivetaku/vibe-sunsang) | 바이브코더를 위한 AI 멘토 에이전트 — 대화 분석, 멘토링, 성장 리포트 |
| [deep-research](https://github.com/fivetaku/deep-research-kit) | 멀티에이전트 딥리서치 — 7단계 파이프라인, 소스 검증, 품질 등급 |
| [pumasi](https://github.com/fivetaku/pumasi) | Claude가 PM, Codex CLI가 병렬 외주 개발자 — 대규모 병렬 코딩 |
| [show-me-the-prd](https://github.com/fivetaku/show-me-the-prd) | 인터뷰 기반 PRD 생성 — 한 문장에서 4종 디자인 문서까지 |
| [kkirikkiri](https://github.com/fivetaku/kkirikkiri) | 자연어 한마디로 AI 에이전트 팀 자동 구성 — 멀티 모델 지원 |
| [skillers-suda](https://github.com/fivetaku/skillers-suda) | 4명의 전문가가 수다 떨면서 아이디어를 동작하는 스킬로 변환 |
| [nopal](https://github.com/fivetaku/nopal) | Google Workspace 오케스트레이션 — 9개 서비스를 자연어로 조합 |
| [insane-search](https://github.com/fivetaku/insane-search) | 차단된 사이트 자동 우회 — Phase 0→3 적응형 스케줄러, 무인증 |
| [insane-design](https://github.com/fivetaku/insane-design) | 웹사이트 CSS를 디자인 시스템으로 분석 — URL에서 디자인 토큰 추출 |

> 플러그인은 계속 추가됩니다. Watch 해두시면 새 플러그인 알림을 받을 수 있습니다.

---

## 요구사항

- **[Claude Code](https://docs.anthropic.com/en/docs/claude-code)** 전용 — Codex, Antigravity 등 다른 AI 코딩 도구는 미지원
- **Windows**: WSL2 위에서 Claude Code 실행 필요 (`wsl --install`)
- **macOS / Linux**: 바로 사용 가능

일부 플러그인은 선택적 도구(`gh`, `yt-dlp`, Playwright MCP 등)가 필요하며, 필요 시 자동 설치됩니다.

---

## 기여

새 플러그인 아이디어나 개선 제안 → [Issues](https://github.com/fivetaku/gptaku_plugins/issues)

---

## 라이선스

MIT

---

<div align="center">

**벽 하나씩, AI Native가 되어갑니다.**

</div>
