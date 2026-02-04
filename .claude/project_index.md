# JavSP 项目索引

> 自动生成的项目结构索引文件，用于快速了解代码库

## 项目概览

**JavSP (Jav Scraper Package)** 是一个自动化的视频元数据抓取和整理工具。它能从文件名中提取视频ID，从多个网站聚合数据，并创建与 Emby、Jellyfin、Kodi 等媒体服务器兼容的标准化元数据文件 (NFO)。

- **仓库**: https://github.com/Yuukiy/JavSP
- **许可证**: GPL-3.0 + Anti 996 License
- **Python 版本**: 3.10 - 3.12

---

## 目录结构

```
/home/user/sp
├── javsp/                    # 主程序包
│   ├── __main__.py          # 入口点 (核心调度)
│   ├── config.py            # 配置管理 (Pydantic)
│   ├── avid.py              # 视频ID提取与识别
│   ├── datatype.py          # 核心数据结构
│   ├── lib.py               # 工具函数
│   ├── func.py              # 业务逻辑函数
│   ├── file.py              # 文件操作
│   ├── nfo.py               # NFO元数据文件生成
│   ├── image.py             # 图片处理 (PIL)
│   ├── chromium.py          # 浏览器Cookie提取
│   ├── print.py             # 控制台输出
│   ├── prompt.py            # 用户交互
│   ├── server.py            # Web服务器 (FastAPI)
│   ├── web_ui/              # Web控制面板前端
│   │   └── index.html       # Web界面
│   ├── web/                 # 网络爬虫模块 (28个爬虫)
│   │   ├── base.py          # HTTP请求基础层
│   │   ├── exceptions.py    # 自定义异常
│   │   ├── translate.py     # 翻译接口
│   │   ├── proxyfree.py     # 代理管理
│   │   └── [爬虫模块...]    # 各网站爬虫
│   └── cropper/             # 图片裁剪 (AI人脸检测)
│
├── data/                    # 静态数据和映射文件
│   ├── actress_alias.json   # 演员名称映射
│   └── genre_*.csv          # 类型翻译映射
│
├── unittest/                # 测试套件
│   ├── conftest.py          # pytest配置
│   ├── test_*.py            # 测试模块
│   └── data/                # 测试数据
│
├── tools/                   # 开发和部署工具
├── docker/                  # Docker支持
├── .github/                 # GitHub Actions工作流
├── image/                   # Logo和图标资源
│
├── config.yml               # 默认配置文件
├── pyproject.toml           # Poetry项目配置
├── setup.py                 # cx_Freeze构建配置
└── poetry.lock              # 锁定的依赖版本
```

---

## 关键文件索引

### 入口点和核心模块

| 文件 | 用途 | 行数 |
|------|------|------|
| `javsp/__main__.py` | 主程序入口点 | 625 |
| `javsp/server.py` | Web服务器 (FastAPI) | 350+ |
| `javsp/config.py` | 配置管理 | 238 |
| `javsp/avid.py` | 视频ID提取 | 154 |
| `javsp/datatype.py` | 数据结构定义 | 228 |
| `javsp/web/base.py` | HTTP请求层 | 250+ |
| `config.yml` | 默认配置 | 199 |

### 网络爬虫模块 (javsp/web/)

| 模块 | 目标网站 | 特殊功能 |
|------|----------|----------|
| `javbus.py` | JAVBUS | 主流站点 |
| `javdb.py` | JAVDB | 复杂解析 (14KB) |
| `javlib.py` | JAVLIB | 主流站点 |
| `fanza.py` | FANZA/DMM | CID支持 |
| `mgstage.py` | MGSTAGE | 高级站点 |
| `fc2.py` | FC2 | 无码内容 |
| `airav.py` | AIRAV | 无码内容 |
| `arzon.py` | ARZON | 购买信息 |
| `translate.py` | 翻译服务 | Google/Baidu/Bing/Claude/OpenAI |

### 数据文件 (data/)

| 文件 | 用途 |
|------|------|
| `actress_alias.json` | 演员名称标准化映射 |
| `genre_avsox.csv` | AVSOX类型翻译 |
| `genre_javbus.csv` | JAVBUS类型翻译 |
| `genre_javdb.csv` | JAVDB类型翻译 |
| `genre_javlib.csv` | JAVLIB类型翻译 |

---

## 技术栈

### 核心依赖

```
requests==2.31.0          # HTTP客户端
lxml>=5.2.1               # XML/HTML解析
pillow==10.2.0            # 图片处理
cloudscraper==1.2.71      # CloudFlare绕过
pydantic>=2.0             # 数据验证
confz>=2.0.1              # 配置管理
pendulum>=3.0.0           # 日期时间处理
colorama==0.4.4           # 终端颜色
tqdm==4.59.0              # 进度条
fastapi>=0.109.0          # Web框架
uvicorn>=0.27.0           # ASGI服务器
pyyaml>=6.0.1             # YAML解析
```

### 开发工具

```
pytest>=8.1.1             # 测试框架
flake8>=7.0.0             # 代码检查
cx-freeze>=7.2.2          # 可执行文件构建
```

### 构建系统

- **包管理**: Poetry
- **版本管理**: poetry-dynamic-versioning
- **可执行文件**: cx_Freeze
- **容器化**: Docker (多阶段构建)

---

## 架构流程

```
用户输入/CLI
    ↓
配置加载 (YAML + CLI参数 + 环境变量)
    ↓
目录扫描 → 视频ID提取 (正则表达式)
    ↓
创建Movie对象 (关联文件)
    ↓
并行网络爬取 (28个不同爬虫)
    ↓
数据聚合与汇总
    ↓
翻译 (可选 - 多引擎支持)
    ↓
文件整理 & NFO生成
    ↓
输出 (整理后的文件 + 元数据)
```

---

## 核心数据结构

### MovieInfo 类 (datatype.py)

```python
MovieInfo:
  - dvdid: str              # DVD ID (番号)
  - cid: str                # DMM Content ID
  - url: str                # 影片页面URL
  - title: str              # 影片标题
  - ori_title: str          # 原始标题 (翻译前)
  - plot: str               # 剧情简介
  - cover: str              # 封面图URL
  - big_cover: str          # 高清封面URL
  - genre: List[str]        # 类型标签
  - score: str              # 评分
  - actress: List[str]      # 演员列表
  - director: str           # 导演
  - duration: str           # 时长(分钟)
  - producer: str           # 制作公司
  - publisher: str          # 发行商
  - publish_date: str       # 发行日期
```

### Movie 类 (datatype.py)

```python
Movie:
  - dvdid/cid: str          # 内容标识符
  - files: List[str]        # 关联的视频文件
  - info: MovieInfo         # 抓取的元数据
  - data_src: str           # 数据源类型
  - save_dir: str           # 输出目录
  - basename: str           # 文件名
  - nfo_file: str           # NFO文件路径
  - poster_file: str        # 封面图路径
```

---

## 配置系统

配置文件: `config.yml`

### 主要配置节

1. **scanner** - 文件扫描设置
   - 视频文件模式和扩展名
   - 最小文件大小
   - ID提取正则表达式

2. **network** - 网络设置
   - 代理服务器支持
   - 重试次数和超时

3. **crawler** - 爬虫设置
   - 爬虫选择
   - 必需字段
   - 封面选择策略

4. **summarizer** - 输出设置
   - 文件组织模式
   - 命名规则
   - NFO生成选项

5. **translator** - 翻译设置
   - 翻译引擎选择
   - 需翻译的字段

### 配置优先级

1. CLI参数 (`--oscanner.input_directory`)
2. 环境变量 (`JAVSP_SCANNER.INPUT_DIRECTORY`)
3. YAML配置文件

---

## 测试

### 测试文件

| 文件 | 用途 |
|------|------|
| `test_crawlers.py` | 爬虫功能验证 (45+用例) |
| `test_avid.py` | 视频ID提取测试 |
| `test_file.py` | 文件操作测试 |
| `test_func.py` | 业务逻辑测试 |
| `test_lib.py` | 工具函数测试 |

### 运行测试

```bash
poetry run pytest                    # 运行所有测试
poetry run pytest unittest/test_crawlers.py  # 只运行爬虫测试
```

---

## Web 控制面板

JavSP 提供了一个基于 Web 的控制面板，可以通过浏览器启动/停止刮削任务和管理配置。

### 启动 Web 服务器

```bash
# 使用 Poetry 运行
poetry run server

# 或者直接运行
python -m javsp.server
```

默认访问地址: `http://localhost:8080`

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `JAVSP_HOST` | `0.0.0.0` | 监听地址 |
| `JAVSP_PORT` | `8080` | 监听端口 |

### API 接口

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/status` | GET | 获取当前任务状态 |
| `/api/config` | GET | 获取配置 |
| `/api/config` | POST | 更新配置 |
| `/api/task/start` | POST | 启动刮削任务 |
| `/api/task/stop` | POST | 停止刮削任务 |
| `/api/directories` | GET | 浏览目录 |

### 功能特性

- 实时任务状态监控
- 目录浏览器选择扫描路径
- 配置在线编辑和保存
- 运行日志实时显示
- 错误信息汇总

---

## 快速开始

### 安装

```bash
# 使用Poetry安装依赖
poetry install

# 运行命令行程序
poetry run javsp

# 运行Web控制面板
poetry run server
```

### Docker

```bash
docker build -f docker/Dockerfile -t javsp:latest .
docker run -v /path/to/videos:/data javsp:latest
```

---

## 异常处理

```
CrawlerError (基类)
├── MovieNotFoundError     # 未找到影片
├── MovieDuplicateError    # 重复影片
├── SiteBlocked            # 网站被封锁
├── SitePermissionError    # 访问被拒绝
├── CredentialError        # 凭证缺失
└── WebsiteError           # HTTP状态码错误
```

---

## 统计信息

| 指标 | 数量 |
|------|------|
| Python文件总数 | 53 |
| 网络爬虫模块 | 28 |
| 配置选项 | 50+ |
| 支持的视频ID格式 | 28+ |
| 测试文件 | 8 |
| 测试数据文件 | 45+ |
| 核心代码行数 | 3000+ |
| 直接依赖 | 20+ |
| 视频格式扩展名 | 23 |

---

*索引生成时间: 2026-02-04*
