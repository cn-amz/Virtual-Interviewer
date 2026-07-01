# Login And Dashboard Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a minimal local login system and a post-login dashboard so users choose interview, ability tree, or reports before entering the interview page.

**Architecture:** Keep the current JSON-first local architecture. Backend adds a lightweight auth router with demo/local users, bearer session tokens, and a `get_current_user` dependency. Frontend adds login state, dashboard navigation, and an ability-tree placeholder without adding a router dependency.

**Tech Stack:** FastAPI, Pydantic, JSON file storage, React, Vite, TypeScript.

---

## File Map

- Create `services/api/app/auth.py`: password hashing, token generation, session lookup, demo user bootstrap.
- Create `services/api/app/routers/auth.py`: `/api/auth/login`, `/api/auth/logout`, `/api/auth/me`.
- Modify `services/api/app/storage.py`: create `users` and `sessions` JSON directories with read/write helpers.
- Modify `services/api/app/models.py`: add auth request/response/user models.
- Modify `services/api/app/main.py`: register auth router.
- Modify `services/api/app/routers/interviews.py`: accept optional authenticated user for report/ability-tree ownership where easy.
- Create `services/api/tests/test_auth.py`: backend auth tests.
- Modify `apps/web/src/api/client.ts`: auth API helpers and bearer token support.
- Create `apps/web/src/pages/LoginPage.tsx`: login form with demo defaults.
- Create `apps/web/src/pages/DashboardPage.tsx`: module selection before interview.
- Create `apps/web/src/pages/AbilityTreePage.tsx`: phase-two placeholder page.
- Modify `apps/web/src/App.tsx`: app state becomes login -> dashboard -> interview/report/ability tree.
- Modify existing frontend pages to fix visible mojibake text touched by phase-two flow.

## Task 1: Backend Auth And Session

**Files:**
- Create: `services/api/app/auth.py`
- Create: `services/api/app/routers/auth.py`
- Modify: `services/api/app/storage.py`
- Modify: `services/api/app/models.py`
- Modify: `services/api/app/main.py`
- Test: `services/api/tests/test_auth.py`

- [ ] **Step 1: Add failing tests**

Create tests for:

```python
def test_login_demo_user_returns_token_and_user()
def test_me_returns_user_for_bearer_token()
def test_me_rejects_missing_token()
def test_logout_invalidates_token()
```

Expected before implementation: imports/routes fail.

- [ ] **Step 2: Add minimal models**

Add Pydantic models:

```python
class LoginRequest(BaseModel):
    username: str
    password: str

class UserPublic(BaseModel):
    user_id: str
    username: str
    display_name: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
```

- [ ] **Step 3: Add JSON storage helpers**

`JsonStorage` should create `users/` and `sessions/`, then support:

```python
read_user(username: str) -> dict | None
write_user(username: str, payload: dict) -> Path
read_session(token: str) -> dict | None
write_session(token: str, payload: dict) -> Path
delete_session(token: str) -> None
```

- [ ] **Step 4: Add auth service**

Use standard library only:

```python
hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
secrets.token_urlsafe(32)
```

Bootstrap demo user when missing:

```text
username: demo
password: demo123456
display_name: 演示用户
user_id: demo
```

- [ ] **Step 5: Add auth router**

Routes:

```text
POST /api/auth/login
POST /api/auth/logout
GET  /api/auth/me
```

Use `Authorization: Bearer <token>`.

- [ ] **Step 6: Register router and run tests**

Run:

```powershell
cd services/api
.\.venv\Scripts\pytest tests\test_auth.py -q
.\.venv\Scripts\pytest -q
```

Expected: all tests pass.

## Task 2: Frontend Login And Dashboard

**Files:**
- Modify: `apps/web/src/api/client.ts`
- Create: `apps/web/src/pages/LoginPage.tsx`
- Create: `apps/web/src/pages/DashboardPage.tsx`
- Create: `apps/web/src/pages/AbilityTreePage.tsx`
- Modify: `apps/web/src/App.tsx`
- Modify: `apps/web/src/pages/SetupPage.tsx`
- Modify: `apps/web/src/pages/InterviewPage.tsx`
- Modify: `apps/web/src/pages/ReportPage.tsx`
- Modify: `apps/web/src/styles.css`

- [ ] **Step 1: Add API helpers**

Add:

```typescript
login(username: string, password: string): Promise<LoginResponse>
getCurrentUser(token: string): Promise<UserPublic>
logout(token: string): Promise<void>
```

- [ ] **Step 2: Add login page**

Default fields:

```text
username: demo
password: demo123456
```

On success, store token in `localStorage` and enter dashboard.

- [ ] **Step 3: Add dashboard page**

Cards:

```text
开始模拟面试
查看能力树
历史报告
管理简历与岗位
```

Only first two need navigation. The other two can be disabled/phase-two placeholders.

- [ ] **Step 4: Update app flow**

State flow:

```text
login -> dashboard -> setup -> interview -> report
                 \-> abilityTree
```

If `localStorage` has token, call `/api/auth/me` on load.

- [ ] **Step 5: Fix visible mojibake in touched pages**

Replace corrupted Chinese strings in setup/interview/report pages with clean Chinese.

- [ ] **Step 6: Build**

Run:

```powershell
cd apps/web
npm run build
```

Expected: TypeScript and Vite build pass.

## Task 3: Integration, Docs, And Issue Tracking

**Files:**
- Modify: `README_CN.md`
- Modify: `docs/prd-phase-roadmap.md`
- Modify: `docs/progress.md`
- Modify: `docs/issues.md` only if a bug is found.

- [ ] **Step 1: Document login usage**

Add demo login:

```text
用户名：demo
密码：demo123456
```

- [ ] **Step 2: Document phase-two status**

Update progress with login/dashboard implementation status and remaining gaps.

- [ ] **Step 3: Final verification**

Run:

```powershell
cd services/api
.\.venv\Scripts\pytest -q

cd ..\..\apps\web
npm run build
```

Expected: both pass.
