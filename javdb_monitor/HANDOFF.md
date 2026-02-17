# JAVDB 磁力链接自动监控工具 — 项目交接文档

## 1. 项目背景与需求

### 用户场景

用户经常在 JAVDB（javdb.com）上通过标签筛选浏览含有磁力链接的影片，手动检查是否有新更新，再将磁力链接保存到迅雷云盘。这个过程是重复性的人工操作，用户希望将其自动化。

### 核心需求

1. **按标签筛选抓取**：两个标签（足交、戀腿癖），各自与「含磁鏈」取交集
2. **定期检查新增**：每个标签检查最近 3 页内容，跳过已获取的影片
3. **去重**：同一番号不重复抓取，两个标签筛出重复番号时只抓一次
4. **磁力链接保存**：当前阶段保存到本地 txt 文件（后续可能集成迅雷云盘/PikPak）
5. **降低被检测风险**：用户明确接受效率不高，要求以「模拟真人浏览器操作」的方式进行，而非纯 HTTP 爬虫

### 已确认的标签筛选 URL

| 标签 | URL | 参数含义 |
|------|-----|---------|
| 足交 + 含磁鏈 | `https://javdb.com/tags?c5=61&c10=1` | c5=61 是足交的分类ID，c10=1 是含磁鏈过滤器 |
| 戀腿癖 + 含磁鏈 | `https://javdb.com/tags?c1=107&c10=1` | c1=107 是戀腿癖的分类ID，c10=1 是含磁鏈过滤器 |

### 暂不实现（后续需求）

- 迅雷云盘/PikPak 集成（自动提交磁力链接进行离线下载）
- 通知推送（Telegram/微信）
- 定时调度（Cron/APScheduler）

---

## 2. 技术方案选型

### 为什么选 DrissionPage

调研了 4 种浏览器自动化方案后选择 DrissionPage（Python）：

| 方案 | Cloudflare 绕过 | 人类模拟 | 为什么没选 |
|------|----------------|---------|-----------|
| **DrissionPage** | 最优 — 不使用 WebDriver 协议 | 好 — Actions 链 + duration 参数 | **选了这个** |
| Patchright + humanization-playwright | 很好 | 最优（贝塞尔曲线） | 异步代码复杂度高 |
| SeleniumBase UC Mode | 好 | 基础 | WebDriver 断连技巧不够隐蔽 |
| nodriver | 好 | 基础 | 社区小，JAVDB 相关案例少 |

**DrissionPage 核心优势：**
- **不使用 WebDriver 协议** — Cloudflare 检测的首要目标就是 WebDriver 签名，DrissionPage 从底层规避了这一点
- 支持浏览器 profile 持久化 — 登录一次后续自动带 Cookie
- 中文文档和社区活跃，已有人用它爬过 JAVDB
- GitHub 上已有基于 DrissionPage 的 JAVDB 爬虫项目在运行

### 技术栈

- **Python 3.10+**
- **DrissionPage 4.x** — 浏览器自动化（核心依赖）
- **PyYAML** — 配置文件
- **SQLite** — 去重数据库（Python 内置，无需额外安装）

---

## 3. JAVDB 页面结构知识（关键）

以下信息来自对现有仓库 `javsp/web/javdb.py` 的分析，以及调研中找到的 StashApp 社区爬虫。**这些选择器是实现的核心，如果 JAVDB 改版需要优先更新。**

### 3.1 标签列表页（tags 页）

URL 格式：`https://javdb.com/tags?c5=61&c10=1&page=2`

```
页面结构：
├── div.movie-list
│   ├── div.item
│   │   └── a.box                          ← 每个影片卡片
│   │       ├── @href                      ← 影片详情页相对路径 (如 /v/abc123)
│   │       ├── @title                     ← 影片标题
│   │       └── div.video-title
│   │           └── strong                 ← 番号文本 (如 "ABC-123")
│   ├── div.item
│   │   └── a.box ...
│   └── ...
└── nav.pagination
    └── a.pagination-next[rel="next"]      ← 下一页按钮
        └── @href                          ← 下一页 URL
```

**当前代码中的选择器：**
- 影片条目：`css:a.box`
- 番号：`css:.video-title strong`
- 下一页：`css:a.pagination-next[rel="next"]`

### 3.2 影片详情页

URL 格式：`https://javdb.com/v/abc123`

```
页面结构：
├── h2
│   └── strong.current-title               ← 影片标题
├── nav.panel.movie-panel-info
│   ├── div > span                         ← 番号 (dvdid)
│   ├── div > strong[text()="日期:"]       ← 发行日期
│   ├── div > strong[text()="時長:"]       ← 时长
│   ├── div > strong[text()="導演:"]       ← 导演
│   ├── div > strong[text()="片商:"]       ← 片商
│   ├── div > strong[text()="類別:"]       ← 类别标签
│   └── div > strong[text()="演員:"]       ← 演员
└── div.magnet-links（磁力链接区域）
    ├── div.magnet-name.column.is-four-fifths   ← 每个磁力链接行
    │   └── a
    │       ├── @href                           ← magnet:?xt=urn:btih:...
    │       ├── span.name                       ← 文件名
    │       └── span.meta                       ← 文件大小
    ├── div.magnet-name.column.is-four-fifths
    │   └── a ...
    └── ...
```

**当前代码中的选择器：**
- 标题：`css:h2 strong.current-title`
- 日期：`xpath://strong[text()="日期:"]`（取 `.next()` 的文本）
- 磁力链接行：`css:.magnet-name.column.is-four-fifths`
- 磁力 URL：行内 `css:a` 的 `href` 属性
- 文件名：行内 `css:span.name`
- 文件大小：行内 `css:span.meta`

### 3.3 JAVDB 的反爬/认证机制

1. **Cloudflare 防护** — JS 验证 + 可能的 Turnstile CAPTCHA
2. **登录要求** — 标签筛选页和磁力链接区域需要 `_jdb_session` Cookie
3. **IP 限制** — 日本 IP 会被屏蔽（Error 1020）
4. **VIP 限制** — 部分内容重定向到 `/pay` 页面
5. **速率限制** — 频繁请求会触发反爬

### 3.4 认证方式

JAVDB 使用 Cookie `_jdb_session` 维持登录状态。当前方案通过 DrissionPage 的浏览器 profile 持久化来保持登录：
- 首次运行 `--login`，用户在浏览器中手动登录
- 登录状态保存在 `browser_data/` 目录
- 后续运行自动复用该 profile，无需重新登录
- Session 过期时工具会检测到重定向至 `/login`，暂停等待用户手动处理

---

## 4. 项目文件结构

```
javdb_monitor/
├── main.py              # 入口文件 — CLI 解析 + 三个命令 (--login/--stats/默认运行)
├── browser.py           # 浏览器自动化 — HumanBrowser 类（DrissionPage 封装 + 人类行为模拟）
├── db.py                # 数据库 — HistoryDB 类（SQLite 去重）
├── config.yaml          # 配置 — 标签 URL、页数、延迟参数等（已填入实际 URL）
├── requirements.txt     # Python 依赖
├── .gitignore           # 忽略 browser_data/、data/、output/
├── HANDOFF.md           # 本文档
│
├── browser_data/        # [运行时生成，gitignore] 浏览器 profile（含登录 Cookie）
├── data/
│   └── history.db       # [运行时生成，gitignore] SQLite 去重数据库
└── output/
    └── magnets.txt      # [运行时生成，gitignore] 磁力链接输出文件
```

---

## 5. 各模块详细说明

### 5.1 main.py — 入口与流程编排

**三个命令：**

| 命令 | 用途 |
|------|------|
| `python main.py --login` | 打开浏览器，用户手动登录 JAVDB，profile 保存到 browser_data/ |
| `python main.py` | 正式运行：遍历标签 → 翻页 → 进详情页 → 提取磁力 → 写入 txt |
| `python main.py --stats` | 显示已记录的影片数和磁力链接数 |

**主流程 (`cmd_run`) 的详细步骤：**

```
FOR 每个标签 (足交, 戀腿癖):
  FOR 每页 (1 到 max_pages=3):
    1. 导航到标签列表页 URL
    2. 检测是否被重定向到登录页 → 如是，等待手动登录
    3. 模拟浏览（随机滚动 3-6 次）
    4. 提取本页所有影片条目 (番号、URL、标题)
    5. FOR 每个影片:
       a. 检查 SQLite → 已存在则跳过
       b. 导航到详情页
       c. 检测登录 → 如需要，等待
       d. 模拟浏览详情页（滚动 + 停顿）
       e. 提取标题、日期、磁力链接
       f. 存入 SQLite（即使没有磁力链接也记录，避免下次重复访问）
       g. 导航回列表页
    6. 如果本页所有影片都已获取过 → 停止翻页（提前终止优化）
    7. 否则获取下一页 URL，继续

最后：将本次新增的磁力链接追加写入 output/magnets.txt
```

**提前终止逻辑：** 如果某页所有影片都在数据库中（`seen_count == len(videos)`），说明后面的页（更旧的内容）大概率也都已获取，直接停止翻页。这在非首次运行时能显著减少访问量。

### 5.2 browser.py — 浏览器自动化

**HumanBrowser 类** 封装 DrissionPage，核心能力：

| 方法 | 功能 | 人类模拟细节 |
|------|------|------------|
| `human_delay(range)` | 随机等待 | 均匀分布随机值 |
| `human_scroll_down(distance)` | 向下滚动 | 分 3-7 步，加速-减速曲线，每步间随机间隔 |
| `human_scroll_page()` | 浏览整页 | 随机 3-6 次滚动 + 40% 概率停顿"阅读" |
| `human_move_and_click(element)` | 点击元素 | 鼠标移动带 duration(0.3-0.8s) + 30% 概率微小抖动 |
| `navigate(url)` | 导航 | 自动等 Cloudflare + 随机延迟 |
| `_wait_for_cloudflare()` | 等 CF 验证 | 轮询检测 "Just a moment" / "Checking your browser" |
| `is_login_page()` | 检测登录页 | 检查 URL 包含 /login 或 /sign_in |
| `wait_for_login()` | 等待手动登录 | 每 2 秒轮询 URL 是否离开登录页 |
| `get_video_list()` | 提取列表 | 返回 `[{video_id, url, title}]` |
| `get_magnets()` | 提取磁力链接 | 返回 `[{magnet, name, size}]` |
| `get_video_detail()` | 提取详情 | 返回 `{title, date}` |
| `get_next_page_url()` | 获取下一页 | 返回 URL 或 None |

**浏览器启动参数：**
```
--disable-blink-features=AutomationControlled  # 隐藏自动化标记
--window-size=1920,1080                         # 模拟正常窗口
--lang=zh-TW                                    # 繁体中文（JAVDB 默认语言）
--no-sandbox                                    # Linux 环境需要
--disable-gpu                                   # 无图形加速环境需要
--disable-dev-shm-usage                         # Docker/容器环境需要
```

### 5.3 db.py — SQLite 去重

**两张表：**

```sql
-- 影片记录
videos (
    video_id    TEXT PRIMARY KEY,   -- 番号，如 "ABC-123"
    title       TEXT,               -- 标题
    url         TEXT,               -- JAVDB 详情页 URL
    tags        TEXT,               -- 来源标签，逗号分隔，如 "足交,戀腿癖"
    date        TEXT,               -- 发行日期
    created_at  TEXT                -- 首次抓取时间
)

-- 磁力链接
magnets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id    TEXT NOT NULL,      -- 关联番号
    magnet      TEXT NOT NULL,      -- 完整磁力链接
    name        TEXT,               -- 文件名
    size        TEXT,               -- 文件大小
    created_at  TEXT,
    UNIQUE(video_id, magnet)        -- 同一番号的同一磁力链接不重复
)
```

**去重逻辑：**
- `is_seen(video_id)` — 检查番号是否已在 videos 表
- `add_video()` — 如果番号已存在但来自不同标签，合并 tags 字段（如 `"足交"` → `"足交,戀腿癖"`）
- 磁力链接使用 `INSERT OR IGNORE` + `UNIQUE(video_id, magnet)` 约束去重

### 5.4 config.yaml — 配置

配置项已填入用户提供的实际标签 URL。所有延迟参数均为 `[最小值, 最大值]` 区间，运行时取随机值。

### 5.5 输出文件格式

`output/magnets.txt` 采用追加写入，每次运行生成一个时间戳段落：

```
# ========== 2026-02-17 12:14 ==========

# ABC-123  某影片标题
# size: 3.2GB
magnet:?xt=urn:btih:aaaaaaaabbbbbbbb...
# size: 5.1GB
magnet:?xt=urn:btih:ccccccccdddddddd...

# DEF-456  另一个影片标题
# size: 2.8GB
magnet:?xt=urn:btih:eeeeeeeefffffff...
```

---

## 6. 所在仓库的上下文

本工具位于 `javdb_monitor/` 子目录中，宿主仓库是 **JavSP**（`/home/user/sp`）— 一个 JAV 元数据刮削器。JavSP 的 `javsp/web/javdb.py` 中有大量可复用的 JAVDB 选择器和解析逻辑，本工具的选择器就是参考它编写的。

**JavSP 的相关文件（可供参考）：**
- `javsp/web/javdb.py` — JAVDB 爬虫（XPath 选择器、Cookie 处理、错误处理）
- `javsp/web/base.py` — HTTP 请求基础层（cloudscraper、代理）
- `javsp/chromium.py` — 浏览器 Cookie 解密提取（AES-GCM）
- `javsp/web/exceptions.py` — 异常层次结构

---

## 7. 当前状态与已验证内容

### 已完成

- [x] 需求分析和技术方案调研
- [x] DrissionPage 浏览器自动化封装（browser.py）
- [x] 人类行为模拟（滚动、点击、延迟）
- [x] SQLite 去重数据库（db.py）
- [x] 主流程编排和 CLI（main.py）
- [x] 配置文件（已填入实际标签 URL）
- [x] 输出文件生成逻辑
- [x] 语法编译检查（3 个模块全部通过）
- [x] 数据库模块单元测试（去重、标签合并、磁力链接去重均通过）
- [x] 输出文件格式验证

### 未验证（因环境网络限制）

- [ ] **实际访问 JAVDB 进行端到端测试**（开发环境有网络出口白名单，javdb.com 被 403 拦截）
- [ ] Cloudflare 验证是否能自动通过
- [ ] 登录态持久化是否正常工作
- [ ] CSS/XPath 选择器是否与当前 JAVDB 页面匹配
- [ ] 翻页 URL 是否正确提取
- [ ] 磁力链接是否正确提取

---

## 8. 剩余 TODO（待下一步开发）

### P0 — 必须完成

1. **在本地环境进行端到端测试**
   - 安装依赖：`pip install -r requirements.txt`
   - 运行 `python main.py --login` 登录
   - 运行 `python main.py --debug` 进行首次抓取
   - 验证选择器是否正确匹配当前 JAVDB 页面结构
   - 如果选择器不对，打开浏览器 DevTools 检查实际 DOM，更新 browser.py 中的选择器

2. **处理可能的选择器不匹配**
   - JAVDB 可能已改版，上述选择器基于 JavSP 历史代码和调研推断
   - 重点关注：`a.box`、`.video-title strong`、`.magnet-name.column.is-four-fifths`、`a.pagination-next`
   - 建议：首次运行时用 `--debug` 模式，观察日志中的元素查找情况

3. **Cloudflare 处理优化**
   - 如果 Cloudflare 出现 Turnstile CAPTCHA，当前代码只做了 JS 验证的等待
   - 可能需要添加：检测 Turnstile iframe → 暂停等待用户手动完成 → 继续

### P1 — 建议实现

4. **迅雷云盘 / PikPak 集成**
   - 推荐使用 PikPak（迅雷国际版），有成熟的 Python 异步库：`pip install pikpakapi`
   - API 示例：`await client.offline_download("magnet:?xt=urn:btih:...")`
   - 比直接调迅雷云盘 API 稳定得多（迅雷没有官方公开 API）

5. **定时调度**
   - 方案 A：系统 cron（最简单）— `0 9 * * * cd /path/to/javdb_monitor && python main.py`
   - 方案 B：APScheduler（进程内调度）— 适合长期运行的服务形态

6. **通知推送**
   - Telegram Bot API 最简单：一个 HTTP POST 即可发送消息
   - 在 `cmd_run` 结束后，如果 `all_new_results` 非空则发送摘要

### P2 — 可选优化

7. **无头模式稳定性**
   - 当前建议使用有头模式（headless=false）以降低 Cloudflare 检测风险
   - 如需在无图形界面服务器运行，用 `xvfb-run python main.py`（虚拟显示）
   - DrissionPage headless 模式对 Cloudflare 的通过率较低

8. **错误恢复**
   - 当前中途出错会保存已获取的数据，但不会自动重试
   - 可以添加：记录处理到哪个标签的哪一页，下次运行从断点继续

9. **代理支持**
   - 如果需要通过代理访问 JAVDB，在 browser.py 中添加：
   ```python
   co.set_proxy(f'http://host:port')  # 或 socks5://host:port
   ```

---

## 9. 已知风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Cloudflare 更新检测机制 | 无法访问 JAVDB | DrissionPage 无 WebDriver 签名是最强基础；社区会持续更新 |
| JAVDB 页面改版 | CSS 选择器失效 | 需手动检查 DOM 并更新 browser.py 中的选择器 |
| 登录 Session 过期 | 无法访问标签筛选页和磁力链接 | 代码会检测并暂停等待手动重新登录 |
| IP 被临时封禁 | 请求被拦截 | 延迟参数已设置较保守的区间，可进一步调大 |
| DrissionPage 与特定 Chromium 版本不兼容 | 浏览器启动失败或页面无法渲染 | 推荐使用系统安装的 Chrome/Chromium，而非 Playwright 捆绑版 |

---

## 10. 快速上手命令

```bash
# 进入项目目录
cd javdb_monitor

# 安装依赖
pip install -r requirements.txt

# 首次：打开浏览器登录 JAVDB（标签 URL 已配置好）
python main.py --login

# 运行抓取（调试模式，看详细日志）
python main.py --debug

# 正常运行
python main.py

# 查看统计
python main.py --stats

# 查看输出
cat output/magnets.txt
```
