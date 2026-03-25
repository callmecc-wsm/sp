const http = require('http');
const fs   = require('fs');
const path = require('path');

const PORT       = process.env.PORT || 3000;
const DATA_FILE  = path.join(__dirname, 'data', 'signups.json');
const TOTAL_SLOTS = 50;

// ===== 工具：读取报名数据 =====
function readSignups() {
  try {
    return JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
  } catch {
    return [];
  }
}

// ===== 工具：写入报名数据 =====
function writeSignups(list) {
  fs.writeFileSync(DATA_FILE, JSON.stringify(list, null, 2), 'utf8');
}

// ===== 工具：解析请求 body =====
function parseBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', chunk => (body += chunk));
    req.on('end', () => {
      try { resolve(JSON.parse(body || '{}')); }
      catch { reject(new Error('Invalid JSON')); }
    });
    req.on('error', reject);
  });
}

// ===== 工具：静态文件 =====
const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css':  'text/css',
  '.js':   'application/javascript',
  '.json': 'application/json',
  '.png':  'image/png',
  '.jpg':  'image/jpeg',
  '.svg':  'image/svg+xml',
  '.ico':  'image/x-icon',
};

function serveFile(res, filePath) {
  const ext  = path.extname(filePath).toLowerCase();
  const mime = MIME[ext] || 'application/octet-stream';
  try {
    const data = fs.readFileSync(filePath);
    res.writeHead(200, { 'Content-Type': mime });
    res.end(data);
  } catch {
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    res.end('Not found');
  }
}

function json(res, status, obj) {
  res.writeHead(status, {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
  });
  res.end(JSON.stringify(obj));
}

// ===== 初始化数据目录 =====
if (!fs.existsSync(path.dirname(DATA_FILE))) {
  fs.mkdirSync(path.dirname(DATA_FILE), { recursive: true });
}
if (!fs.existsSync(DATA_FILE)) {
  writeSignups([]);
  console.log('已初始化报名数据文件：', DATA_FILE);
}

// ===== 服务器 =====
const server = http.createServer(async (req, res) => {
  const url    = req.url.split('?')[0];
  const method = req.method.toUpperCase();

  // CORS preflight
  if (method === 'OPTIONS') {
    res.writeHead(204, { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'Content-Type' });
    res.end();
    return;
  }

  // ── GET /api/count ──────────────────────────────────────────
  if (method === 'GET' && url === '/api/count') {
    const signups = readSignups();
    json(res, 200, { count: signups.length, total: TOTAL_SLOTS });
    return;
  }

  // ── POST /api/signup ────────────────────────────────────────
  if (method === 'POST' && url === '/api/signup') {
    let body;
    try { body = await parseBody(req); }
    catch { json(res, 400, { message: '请求格式错误' }); return; }

    const { name, dept, phone, shuttle, diet, note } = body;

    // 简单校验
    if (!name || !dept || !phone || !shuttle) {
      json(res, 400, { message: '请填写所有必填项' });
      return;
    }
    if (!/^1[3-9]\d{9}$/.test(phone)) {
      json(res, 400, { message: '手机号格式不正确' });
      return;
    }

    const signups = readSignups();

    // 名额检查
    if (signups.length >= TOTAL_SLOTS) {
      json(res, 400, { message: '报名名额已满，感谢您的参与！' });
      return;
    }

    // 重复报名检查（同一手机号）
    if (signups.some(s => s.phone === phone)) {
      json(res, 400, { message: '该手机号已报名，请勿重复提交' });
      return;
    }

    const record = {
      id:        signups.length + 1,
      name:      name.trim(),
      dept,
      phone,
      shuttle,
      diet:      diet || '无特殊要求',
      note:      note || '',
      createdAt: new Date().toISOString(),
    };

    signups.push(record);
    writeSignups(signups);

    console.log(`[报名] #${record.id} ${record.name} (${record.dept}) - ${new Date().toLocaleString('zh-CN')}`);

    json(res, 200, { message: '报名成功', count: signups.length, total: TOTAL_SLOTS });
    return;
  }

  // ── GET /api/signups  (查看所有报名，可加密码保护) ──────────
  if (method === 'GET' && url === '/api/signups') {
    const signups = readSignups();
    // 脱敏：手机号中间4位打码
    const masked = signups.map(s => ({
      ...s,
      phone: s.phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2'),
    }));
    json(res, 200, { count: signups.length, total: TOTAL_SLOTS, signups: masked });
    return;
  }

  // ── 静态文件 ────────────────────────────────────────────────
  let filePath;
  if (url === '/' || url === '/index.html') {
    filePath = path.join(__dirname, 'index.html');
  } else {
    filePath = path.join(__dirname, url);
  }

  // 安全：防止路径穿越
  if (!filePath.startsWith(__dirname)) {
    res.writeHead(403); res.end('Forbidden'); return;
  }

  serveFile(res, filePath);
});

server.listen(PORT, () => {
  console.log(`\n✅  服务已启动：http://localhost:${PORT}\n`);
  console.log('   报名数据存储在：', DATA_FILE);
  console.log('   查看所有报名：   http://localhost:' + PORT + '/api/signups\n');
});

server.on('error', err => {
  if (err.code === 'EADDRINUSE') {
    console.error(`端口 ${PORT} 已被占用，请换一个端口：PORT=3001 node server.js`);
  } else {
    console.error('服务器错误：', err);
  }
  process.exit(1);
});
