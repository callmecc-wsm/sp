# 2025 夏日团建 · 报名页面

纯 HTML + Node.js 实现的活动报名页面，无需安装任何依赖，开箱即用。

---

## 快速启动

```bash
cd teambuilding
node server.js
```

浏览器打开 http://localhost:3000 即可看到报名页面。

默认端口 3000，如需更换：

```bash
PORT=8080 node server.js
```

---

## 目录结构

```
teambuilding/
├── index.html        # 前端页面（全部样式和逻辑在此一个文件）
├── server.js         # 后端服务（Node.js 原生 http 模块，无需安装依赖）
├── package.json      # 项目配置
├── data/
│   └── signups.json  # 报名数据（自动生成，JSON 格式）
└── README.md
```

---

## 查看报名数据

**方式一：直接查看文件**

```bash
cat data/signups.json
```

**方式二：浏览器 / curl 查看（手机号已脱敏）**

```
http://localhost:3000/api/signups
```

---

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | /api/count   | 获取当前报名人数 |
| POST | /api/signup  | 提交报名（JSON Body） |
| GET  | /api/signups | 查看全部报名列表（手机号脱敏） |

**POST /api/signup 请求体示例：**

```json
{
  "name":    "张三",
  "dept":    "技术部",
  "phone":   "13812345678",
  "shuttle": "是，需要班车",
  "diet":    "无特殊要求",
  "note":    "备注内容（可为空）"
}
```

---

## 修改活动信息

活动名称、时间、地点、日程等均在 `index.html` 中，直接搜索对应文字修改即可。

- **活动基本信息**：搜索 `hero-meta` 附近的文字
- **信息格子**（日期/时间/地点/人数）：搜索 `info-grid` 附近
- **日程安排**：搜索 `timeline` 附近的 `<li>` 列表
- **人数上限**：`index.html` 中的 `totalCount = 50` 以及 `server.js` 中的 `TOTAL_SLOTS = 50`

---

## 修改部门列表

在 `index.html` 中搜索 `<select id="dept">`，修改其中的 `<option>` 列表。

---

## 部署到服务器

**方式一：直接运行**

```bash
# 安装 Node.js (>= 18) 后直接启动
PORT=80 node server.js
```

**方式二：使用 PM2 保持后台运行（推荐）**

```bash
npm install -g pm2
pm2 start server.js --name teambuilding
pm2 save
pm2 startup    # 设置开机自启
```

**方式三：Docker**

```bash
docker run -d \
  -p 3000:3000 \
  -v $(pwd)/data:/app/data \
  -w /app \
  node:18-alpine \
  node server.js
```

---

## 注意事项

- 报名数据存在 `data/signups.json`，**部署时请确保该文件有写权限**
- 同一手机号只能报名一次，会自动拦截重复提交
- 名额满 50 人后自动关闭报名
- 如需导出 Excel，可将 `signups.json` 内容粘贴到 [jsontoexcel.com](https://jsontoexcel.com/) 转换
