"""
JavSP Web Server - 提供 Web 界面控制刮削任务
"""

import os
import sys
import json
import yaml
import logging
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('javsp.server')


class TaskStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    STOPPING = "stopping"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ScrapeTask:
    """刮削任务状态"""
    status: TaskStatus = TaskStatus.IDLE
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    total_movies: int = 0
    processed_movies: int = 0
    current_movie: str = ""
    errors: List[str] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "status": self.status.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_movies": self.total_movies,
            "processed_movies": self.processed_movies,
            "current_movie": self.current_movie,
            "errors": self.errors[-50:],  # 只保留最近50条错误
            "logs": self.logs[-100:],  # 只保留最近100条日志
        }


# 全局任务状态
current_task = ScrapeTask()
task_lock = threading.Lock()
stop_flag = threading.Event()


# Pydantic 模型
class ConfigUpdate(BaseModel):
    """配置更新请求"""
    scanner_input_directory: Optional[str] = None
    scanner_minimum_size: Optional[str] = None
    scanner_skip_nfo_dir: Optional[bool] = None
    scanner_manual: Optional[bool] = None
    network_proxy_server: Optional[str] = None
    network_retry: Optional[int] = None
    crawler_hardworking: Optional[bool] = None
    crawler_normalize_actress_name: Optional[bool] = None
    summarizer_move_files: Optional[bool] = None
    summarizer_path_output_folder_pattern: Optional[str] = None
    summarizer_path_hard_link: Optional[bool] = None
    summarizer_cover_highres: Optional[bool] = None
    translator_engine: Optional[str] = None


class StartTaskRequest(BaseModel):
    """启动任务请求"""
    input_directory: Optional[str] = None


# 创建 FastAPI 应用
app = FastAPI(
    title="JavSP Web Control Panel",
    description="JavSP 刮削任务 Web 控制面板",
    version="1.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_config_path() -> Path:
    """获取配置文件路径"""
    from javsp.lib import resource_path
    return Path(resource_path('config.yml'))


def load_config() -> dict:
    """加载配置文件"""
    config_path = get_config_path()
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}


def save_config(config: dict):
    """保存配置文件"""
    config_path = get_config_path()
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def add_log(message: str):
    """添加日志消息"""
    global current_task
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    with task_lock:
        current_task.logs.append(log_entry)
    logger.info(message)


def run_scrape_task(input_directory: Optional[str] = None):
    """运行刮削任务"""
    global current_task, stop_flag

    try:
        with task_lock:
            current_task.status = TaskStatus.RUNNING
            current_task.start_time = datetime.now().isoformat()
            current_task.end_time = None
            current_task.total_movies = 0
            current_task.processed_movies = 0
            current_task.current_movie = ""
            current_task.errors = []
            current_task.logs = []

        add_log("开始刮削任务...")

        # 导入核心模块
        from javsp.config import Cfg
        from javsp.file import scan_movies, get_scan_dir
        from javsp.func import check_update

        # 重新加载配置
        # 注意：这里需要重置配置单例
        import importlib
        import javsp.config
        importlib.reload(javsp.config)
        from javsp.config import Cfg

        # 获取扫描目录
        if input_directory:
            root = input_directory
        else:
            root = Cfg().scanner.input_directory
            if root:
                root = str(root)

        if not root or not os.path.isdir(root):
            raise ValueError(f"无效的扫描目录: {root}")

        add_log(f"扫描目录: {root}")

        # 导入爬虫
        from javsp.__main__ import import_crawlers
        import_crawlers()

        # 扫描影片
        add_log("正在扫描影片文件...")
        recognized = scan_movies(root)

        with task_lock:
            current_task.total_movies = len(recognized)

        if not recognized:
            add_log("未找到影片文件")
            with task_lock:
                current_task.status = TaskStatus.COMPLETED
                current_task.end_time = datetime.now().isoformat()
            return

        add_log(f"找到 {len(recognized)} 部影片")

        # 导入处理函数
        from javsp.__main__ import parallel_crawler, info_summary, generate_names, download_cover, process_poster
        from javsp.nfo import write_nfo

        os.chdir(root)

        # 处理每部影片
        for i, movie in enumerate(recognized):
            # 检查停止标志
            if stop_flag.is_set():
                add_log("任务被用户停止")
                with task_lock:
                    current_task.status = TaskStatus.STOPPING
                break

            movie_id = repr(movie)[7:-2]
            with task_lock:
                current_task.current_movie = movie_id
                current_task.processed_movies = i

            add_log(f"正在处理 [{i+1}/{len(recognized)}]: {movie_id}")

            try:
                # 抓取数据
                all_info = parallel_crawler(movie)
                if not all_info:
                    add_log(f"  跳过: 未获取到信息")
                    with task_lock:
                        current_task.errors.append(f"{movie_id}: 未获取到信息")
                    continue

                # 汇总数据
                if not info_summary(movie, all_info):
                    add_log(f"  跳过: 缺少必需字段")
                    with task_lock:
                        current_task.errors.append(f"{movie_id}: 缺少必需字段")
                    continue

                # 生成文件名
                generate_names(movie)

                if not movie.save_dir:
                    add_log(f"  跳过: 无法生成保存路径")
                    continue

                # 创建目录
                if not os.path.exists(movie.save_dir):
                    os.makedirs(movie.save_dir)

                # 下载封面
                if Cfg().summarizer.cover.highres:
                    cover_result = download_cover(movie.info.covers, movie.fanart_file, movie.info.big_covers)
                else:
                    cover_result = download_cover(movie.info.covers, movie.fanart_file)

                if cover_result:
                    cover, pic_path = cover_result
                    if cover != movie.info.cover:
                        movie.info.cover = cover
                    if pic_path != movie.fanart_file:
                        movie.fanart_file = pic_path
                        actual_ext = os.path.splitext(pic_path)[1]
                        movie.poster_file = os.path.splitext(movie.poster_file)[0] + actual_ext

                    # 处理封面
                    process_poster(movie)

                # 写入 NFO
                write_nfo(movie.info, movie.nfo_file)

                # 移动文件
                if Cfg().summarizer.move_files:
                    movie.rename_files(Cfg().summarizer.path.hard_link)

                add_log(f"  完成: {movie.save_dir}")

            except Exception as e:
                error_msg = f"{movie_id}: {str(e)}"
                add_log(f"  错误: {str(e)}")
                with task_lock:
                    current_task.errors.append(error_msg)

        with task_lock:
            current_task.processed_movies = len(recognized)
            if current_task.status != TaskStatus.STOPPING:
                current_task.status = TaskStatus.COMPLETED
            current_task.end_time = datetime.now().isoformat()

        add_log(f"刮削任务完成，共处理 {len(recognized)} 部影片")

    except Exception as e:
        logger.exception("刮削任务出错")
        add_log(f"任务出错: {str(e)}")
        with task_lock:
            current_task.status = TaskStatus.ERROR
            current_task.end_time = datetime.now().isoformat()
            current_task.errors.append(str(e))
    finally:
        stop_flag.clear()


# API 路由

@app.get("/")
async def index():
    """返回 Web 界面"""
    html_path = Path(__file__).parent / "web_ui" / "index.html"
    if html_path.exists():
        return FileResponse(html_path)
    return HTMLResponse(content="<h1>JavSP Web Control Panel</h1><p>Web UI not found.</p>")


@app.get("/api/status")
async def get_status():
    """获取当前任务状态"""
    with task_lock:
        return current_task.to_dict()


@app.get("/api/config")
async def get_config():
    """获取当前配置"""
    try:
        config = load_config()
        return {
            "success": True,
            "config": config
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/config")
async def update_config(update: ConfigUpdate):
    """更新配置"""
    try:
        config = load_config()

        # 更新 scanner 配置
        if update.scanner_input_directory is not None:
            config.setdefault('scanner', {})['input_directory'] = update.scanner_input_directory or None
        if update.scanner_minimum_size is not None:
            config.setdefault('scanner', {})['minimum_size'] = update.scanner_minimum_size
        if update.scanner_skip_nfo_dir is not None:
            config.setdefault('scanner', {})['skip_nfo_dir'] = update.scanner_skip_nfo_dir
        if update.scanner_manual is not None:
            config.setdefault('scanner', {})['manual'] = update.scanner_manual

        # 更新 network 配置
        if update.network_proxy_server is not None:
            config.setdefault('network', {})['proxy_server'] = update.network_proxy_server or None
        if update.network_retry is not None:
            config.setdefault('network', {})['retry'] = update.network_retry

        # 更新 crawler 配置
        if update.crawler_hardworking is not None:
            config.setdefault('crawler', {})['hardworking'] = update.crawler_hardworking
        if update.crawler_normalize_actress_name is not None:
            config.setdefault('crawler', {})['normalize_actress_name'] = update.crawler_normalize_actress_name

        # 更新 summarizer 配置
        if update.summarizer_move_files is not None:
            config.setdefault('summarizer', {})['move_files'] = update.summarizer_move_files
        if update.summarizer_path_output_folder_pattern is not None:
            config.setdefault('summarizer', {}).setdefault('path', {})['output_folder_pattern'] = update.summarizer_path_output_folder_pattern
        if update.summarizer_path_hard_link is not None:
            config.setdefault('summarizer', {}).setdefault('path', {})['hard_link'] = update.summarizer_path_hard_link
        if update.summarizer_cover_highres is not None:
            config.setdefault('summarizer', {}).setdefault('cover', {})['highres'] = update.summarizer_cover_highres

        # 更新 translator 配置
        if update.translator_engine is not None:
            if update.translator_engine == "" or update.translator_engine == "null":
                config.setdefault('translator', {})['engine'] = None
            else:
                config.setdefault('translator', {})['engine'] = {"name": update.translator_engine}

        save_config(config)

        return {"success": True, "message": "配置已更新"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/task/start")
async def start_task(request: StartTaskRequest, background_tasks: BackgroundTasks):
    """启动刮削任务"""
    global current_task, stop_flag

    with task_lock:
        if current_task.status == TaskStatus.RUNNING:
            raise HTTPException(status_code=400, detail="任务正在运行中")

    stop_flag.clear()
    background_tasks.add_task(run_scrape_task, request.input_directory)

    return {"success": True, "message": "任务已启动"}


@app.post("/api/task/stop")
async def stop_task():
    """停止刮削任务"""
    global current_task, stop_flag

    with task_lock:
        if current_task.status != TaskStatus.RUNNING:
            raise HTTPException(status_code=400, detail="没有正在运行的任务")

    stop_flag.set()
    add_log("正在停止任务...")

    return {"success": True, "message": "正在停止任务"}


@app.get("/api/directories")
async def list_directories(path: str = "/"):
    """列出目录内容"""
    try:
        if not path:
            path = "/"

        path = os.path.expanduser(path)

        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="路径不存在")

        if not os.path.isdir(path):
            raise HTTPException(status_code=400, detail="不是目录")

        items = []
        try:
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                try:
                    is_dir = os.path.isdir(item_path)
                    items.append({
                        "name": item,
                        "path": item_path,
                        "is_dir": is_dir
                    })
                except PermissionError:
                    continue
        except PermissionError:
            raise HTTPException(status_code=403, detail="没有权限访问此目录")

        # 只返回目录，按名称排序
        dirs = sorted([i for i in items if i["is_dir"]], key=lambda x: x["name"].lower())

        return {
            "success": True,
            "path": path,
            "parent": os.path.dirname(path) if path != "/" else None,
            "directories": dirs
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 静态文件服务
web_ui_path = Path(__file__).parent / "web_ui"
if web_ui_path.exists():
    app.mount("/static", StaticFiles(directory=str(web_ui_path)), name="static")


def entry():
    """Web 服务器入口"""
    import uvicorn

    host = os.environ.get("JAVSP_HOST", "0.0.0.0")
    port = int(os.environ.get("JAVSP_PORT", "8080"))

    print(f"JavSP Web Control Panel")
    print(f"访问地址: http://localhost:{port}")
    print(f"按 Ctrl+C 停止服务器")

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    entry()
