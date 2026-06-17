# Flight Claw 业务逻辑与安全审查报告

## 执行摘要

本次审查聚焦业务影响更高的问题，而不是只做通用漏洞扫描。重点检查了 FastAPI 后端和 React 前端中的认证边界、管理类业务动作、扫描调度、任务生成、快照文件访问和 token 处理方式。

最高风险问题是 JWT 签名密钥存在公开默认值 `change-me`。如果生产环境没有配置 `SECRET_KEY`，攻击者可以伪造管理员 token。其次是系统支持把 bearer token 放在 URL query 中访问快照、管理类接口没有角色权限边界、日期和计划任务输入缺少业务限额，可能被滥用来触发大量扫描任务和第三方访问。

## 严重

### BIZ-001：JWT 默认密钥可能导致 token 伪造

- 规则 ID：FASTAPI-AUTH-004
- 严重级别：Critical
- 位置：`app/security/jwt.py`，模块常量及 token 编解码逻辑，行 6-20
- 证据：

```python
SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
...
return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
...
return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
```

- 影响：如果生产环境未配置 `SECRET_KEY`，任何知道源码的人都可以使用默认密钥签发包含 `user_id` 和 `role` 的有效 JWT，并调用所有认证后的 API。监控配置、扫描执行、快照访问、系统设置和城市代码数据都会被完全绕过。
- 修复建议：除本地开发环境外，应用启动时必须强制要求配置高强度随机 `SECRET_KEY`。如果确实需要本地默认值，应通过显式的 `APP_ENV=development` 分支隔离。
- 缓解措施：轮换 `SECRET_KEY`，使旧 token 失效；如果系统曾以默认密钥对外暴露，应审查访问日志。
- 误报条件：只有当部署系统始终注入强随机 `SECRET_KEY`，并且缺失时会阻止启动，风险才会降低。该保证目前未在仓库中体现。

## 高危

### BIZ-002：bearer token 被接受并拼接到快照 URL 中

- 规则 ID：FASTAPI-AUTH-002 / REACT-CONFIG-001 相关 token 处理
- 严重级别：High
- 位置：`app/security/auth.py`，`_extract_token`，行 13-20；`frontend/src/components/common/SnapshotLinks.tsx`，链接构造，行 12-21
- 证据：

```python
if credentials is not None:
    return credentials.credentials
return request.query_params.get("token")
```

```tsx
href={`${taskApi.screenshotUrl(taskId)}?token=${token}`}
target="_blank"
rel="noreferrer"
```

- 影响：URL 中的访问 token 很容易进入浏览器历史、服务端或代理日志、监控系统、复制链接和截图。由于该 token 可调用全部业务 API，一旦泄露，持有者可在过期前修改业务配置、触发扫描和读取数据。
- 修复建议：停止在 `get_current_user` 中接受 `?token=`。快照应通过带 `Authorization` header 的认证请求获取，并以 blob 方式打开新窗口；或者签发只对单个文件有效、短时效、一次性的下载 URL。
- 缓解措施：缩短 token 有效期，增加 token 撤销或版本机制，确保反向代理不记录 query string。
- 误报条件：`rel="noreferrer"` 可减少 Referer 泄漏，但不能防止浏览器历史、复制链接、本地日志或服务端日志记录 URL。

### BIZ-003：管理类业务动作只有登录校验，没有角色或权限校验

- 规则 ID：FASTAPI-AUTHZ-001 / REACT-AUTHZ-001
- 严重级别：如果支持多用户则为 High；如果严格是单用户本地软件则为 Medium
- 位置：`app/routers/api.py`，路由级认证依赖，行 57；修改类接口，行 895-976、1017-1106、1152-1245、1532-1579、1632-1646；`app/security/auth.py`，仅做用户存在性校验，行 39-43
- 证据：

```python
router = APIRouter(prefix="/api", tags=["api"], dependencies=[Depends(get_current_user)])
```

```python
user = db.scalar(select(FlightUser).where(FlightUser.id == user_id))
if user is None or not user.enabled:
    raise HTTPException(status_code=401, detail="...")
return user
```

只依赖通用登录态保护的典型高权限接口：

```python
@router.post("/monitors/{monitor_id}/scan-now")
@router.put("/monitors/{monitor_id}/schedule")
@router.post("/scans/{scan_id}/restart")
@router.post("/tasks/{task_id}/run")
@router.put("/settings")
```

- 影响：任何启用用户都可以创建或删除监控、修改计划任务、运行或重启爬虫、重置任务、解析快照、同步城市代码、修改运行时设置。如果未来加入非管理员用户，前端展示的 `role` 不是安全边界。
- 修复建议：为修改类和运维类接口增加明确依赖，例如 `require_admin` 或更细粒度的权限依赖。只读接口可单独分组，按实际产品需要开放给普通用户。
- 缓解措施：在权限体系完成前，限制系统只能创建一个管理员用户，并在文档中明确这是单用户工具。
- 误报条件：当前代码看起来只初始化管理员用户，但模型、JWT 和接口返回中都包含 `role` 字段，说明系统已具备多角色扩展迹象。

## 中危

### BIZ-004：批量日期缺少范围上限，可能制造过量扫描任务

- 规则 ID：FASTAPI-VALID-001 / 业务资源滥用
- 严重级别：Medium
- 位置：`app/routers/api.py`，`DateBatchPayload`，行 135-159；`app/services/date_service.py`，批量日期展开，行 51-102；`app/services/task_service.py`，任务生成，行 264-360
- 证据：

```python
class DateBatchPayload(BaseModel):
    start_date: date
    end_date: date
    return_start_date: date | None = None
    return_end_date: date | None = None
```

```python
while current <= end_date:
    ...
    depart_dates.append(current)
...
for d in depart_dates:
    for r in return_dates:
```

```python
for monitor_date in dates:
    ...
    for query_type in _query_types(monitor):
        _add_oneway_task(...)
    ...
    for transfer in transfers:
        _add_oneway_task(...)
    ...
    for positioning in positionings:
        _add_oneway_task(...)
```

- 影响：一个认证请求就可以插入大量监控日期。往返场景尤其明显，出发日期和返程日期会形成笛卡尔积。后续手动或定时扫描会把这些日期转成爬虫任务，消耗本机 CPU、浏览器资源，并向第三方站点产生大量请求。
- 修复建议：增加硬性上限，包括单次日期范围长度、单请求可创建行数、每个 monitor 可启用日期数、单次 scan 可生成任务数、往返日期组合数。超过上限应在插入前返回明确校验错误。
- 缓解措施：增加 `MAX_TASKS_PER_SCAN` 等运行时限制，超过上限的 monitor 不允许启动扫描或计划任务。
- 误报条件：这不是未认证攻击，但对任意启用账号或被盗 token 来说，是现实的业务滥用和可用性风险。

### BIZ-005：cron 只校验语法，不限制业务执行频率

- 规则 ID：业务资源滥用
- 严重级别：Medium
- 位置：`app/routers/api.py`，计划任务 payload 和更新逻辑，行 172-184、951-960；`app/services/scheduler_service.py`，cron 注册，行 47-75
- 证据：

```python
schedule_cron: str | None = Field(default=None, max_length=100)
```

```python
monitor.schedule_enabled = payload.schedule_enabled
monitor.schedule_cron = payload.schedule_cron
...
refresh_scheduler()
```

```python
trigger = CronTrigger.from_crontab(
    monitor.schedule_cron,
    timezone=monitor.schedule_timezone or "Asia/Shanghai",
)
```

- 影响：任何认证用户都可以为 monitor 设置高频计划任务。虽然扫描运行器有并发上限，但没有对单个 monitor 的最小执行间隔、每日扫描次数或排队频率做业务限制。
- 修复建议：对 cron 表达式做业务频率校验，例如每个 monitor 不允许低于 N 小时一次；同时增加每 monitor 的每日扫描配额。
- 缓解措施：对频繁出现 `SKIPPED_RUNNING` 或大量 queued scan 的 monitor 做告警。
- 误报条件：`CronTrigger.from_crontab` 只校验语法，不等于业务频率控制。

### BIZ-006：登录和验证码接口缺少限流与验证码签发控制

- 规则 ID：FASTAPI-AUTH-001 相关暴力破解控制
- 严重级别：Medium
- 位置：`app/routers/auth.py`，验证码和登录路由，行 37-53；`app/security/captcha.py`，内存验证码存储，行 15-29、67-87
- 证据：

```python
@router.get("/captcha")
def get_captcha():
    data = generate_captcha()
```

```python
@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    if not verify_captcha(...):
        raise HTTPException(...)
```

```python
_CAPTCHA_STORE: dict[str, tuple[str, float]] = {}
...
_CAPTCHA_STORE[captcha_id] = (code, time.time())
```

- 影响：攻击者可以反复请求验证码，持续扩大进程内存占用直到 TTL 清理；也可以在能解决或绕过验证码的情况下高速尝试登录。验证码只是交互摩擦，不等于限流。
- 修复建议：为验证码签发和登录尝试增加 IP/用户名维度的限流；对用户名增加失败退避或短时锁定；限制验证码存储最大容量。
- 缓解措施：如果系统对公网开放，应先在反向代理层增加限流。
- 误报条件：如果只在本机离线使用，风险会降低。

### BIZ-007：前端将完整 API token 存在 localStorage

- 规则 ID：REACT-AUTH-001 / JS-STORAGE-001
- 严重级别：Medium
- 位置：`frontend/src/api/authApi.ts`，token 存储，行 29-40；`frontend/src/lib/api.ts`，token 使用，行 6-31
- 证据：

```ts
const TOKEN_KEY = "flight_scan_token";
...
localStorage.setItem(TOKEN_KEY, token);
```

```ts
const token = getToken();
if (token) {
  headers["Authorization"] = `Bearer ${token}`;
}
```

- 影响：一旦出现 XSS、浏览器扩展被攻破，或同源脚本被污染，攻击者可以读取长期 bearer token 并调用全部业务 API。该风险会被“缺少权限分级”和“支持 URL token”进一步放大。
- 修复建议：优先改为短生命周期 access token 与刷新/轮换机制，或使用 HttpOnly 服务端会话并配套 CSRF 防护。如果继续使用 localStorage，应缩短 token 生命周期，并补充 CSP/Trusted Types 等前端加固。
- 缓解措施：优先移除 URL token，因为它是更容易泄露 token 的路径。
- 误报条件：本次未在前端搜索到明显的 `dangerouslySetInnerHTML`、直接 `innerHTML`、`eval` 或 `postMessage` 风险点，所以该项主要是降低未来 XSS 的影响面，而不是证明当前已有 XSS 漏洞。

## 低危

### BIZ-008：生产环境可能暴露运维元信息和交互式 API 文档

- 规则 ID：FASTAPI-OPENAPI-001 / REACT-HEADERS-001 相关
- 严重级别：Low 到 Medium，取决于部署暴露面
- 位置：`app/main.py`，默认 FastAPI app，行 42；`app/routers/api.py`，settings 响应，行 1582-1623
- 证据：

```python
app = FastAPI(title="FlightScan")
```

```python
"sqlite_path": str(DATA_DIR / "flight_claw.db"),
"screenshots_path": str(DATA_DIR / "screenshots"),
"text_path": str(DATA_DIR / "text"),
```

- 影响：`/docs` 和 `/openapi.json` 默认开启，认证后的 settings 接口会返回本地文件系统路径。攻击者一旦获得任意 token，可以更快理解 API 面和部署结构。
- 修复建议：生产环境禁用或保护 `/docs`、`/openapi.json`；普通 settings 响应中不要返回绝对文件路径，除非处于管理员故障排查模式。
- 缓解措施：通过网络白名单或反向代理认证限制生产访问。
- 误报条件：本地开发环境保留 docs 是合理的，应做环境隔离，而不是完全删除。

## 正向发现

- `app/security/password.py` 使用 bcrypt 存储密码哈希。
- 主 `/api` 路由具备路由级认证依赖。
- 快照文件响应会解析路径并拒绝 `DATA_DIR` 之外的路径。
- 数据库访问主要使用 SQLAlchemy ORM/query builder；审查路径中未发现明显字符串拼接 SQL 注入点。
- 前端搜索未发现明显 `dangerouslySetInnerHTML`、直接 `innerHTML`、`eval` 或 `postMessage` 风险点。

## 建议修复顺序

1. 在非开发环境强制要求高强度 `SECRET_KEY`，并轮换已有 token。
2. 移除 query string token 支持，用 header 认证下载或短时效文件 URL 替代快照链接。
3. 为修改类和运维类接口增加角色或权限依赖。
4. 为批量日期、单次 scan 任务数、cron 频率和 monitor 扫描配额增加业务上限。
5. 为登录和验证码签发增加限流和失败退避。
6. 重新评估 token 存储方式，并补齐生产环境 docs、响应头和元信息暴露控制。
