# 共福农机库存管理系统

基于 Flask + 原生 JavaScript 的农机配件库存管理系统，支持商品管理、扫码出入库、销售开单、赊账客户管理、商品二维码生成与打印等功能。

## 功能特性

- **今日看板**：商品种类、库存预警、今日销售额、赊账总额、入库/出库统计
- **商品管理**：商品 CRUD、分类、供应商关联、安全库存预警
- **扫码出入库**：摄像头扫码（支持微信内置浏览器）、手动输入编码、批量出入库
- **销售开单**：快速开单、赊账、结清、打印小票
- **入库登记**：采购入库、供应商关联
- **供应商管理**：供应商信息 CRUD
- **赊账客户**：客户欠款跟踪、还款记录
- **商品二维码**：一键生成、打印商品二维码，贴货架方便扫码出入库
- **操作记录**：全操作日志，支持时间范围筛选
- **用户管理**：多用户、角色权限（店长/店员）

## 账号

| 角色 | 账号 | 密码 |
|------|------|------|
| 店长 | owner | 2888 |
| 店员 | clerk | 123456 |

## 技术栈

- **后端**：Python Flask + SQLite
- **前端**：原生 HTML/CSS/JavaScript（无框架依赖）
- **二维码生成**：qrcode-generator + Canvas（PNG 格式）
- **二维码识别**：jsQR + BarcodeDetector API
- **数据存储**：SQLite（零配置，开箱即用）

## 快速开始

```bash
# 安装依赖
pip install flask

# 启动应用
python app.py

# 浏览器访问
# http://localhost:8080
```

## 项目结构

```
gfnj-inventory/
├── app.py                      # Flask 主应用（路由 + API + 数据库）
├── .gitignore
├── static/
│   ├── css/style.css           # 全局样式
│   ├── js/
│   │   ├── common.js           # 公共请求封装
│   │   ├── qrcode.min.js       # 二维码生成库
│   │   ├── jsQR.min.js         # 二维码识别库
│   │   └── scan.js             # 扫码出入库逻辑
│   └── sw.js                   # Service Worker
└── templates/
    ├── login.html              # 登录页（含记住密码功能）
    ├── index.html              # 首页看板
    ├── products.html           # 商品管理
    ├── qrcodes.html            # 商品二维码（PNG 格式）
    ├── scan.html               # 扫码出入库
    ├── sales.html              # 销售开单
    ├── purchases.html          # 入库登记
    ├── suppliers.html          # 供应商管理
    ├── customers.html          # 赊账客户
    ├── logs.html               # 操作记录
    ├── users.html              # 用户管理
    └── product_detail.html     # 商品详情页（扫码入口）
```

## 已修复的问题

### 1. 商品二维码扫描不出来

**问题**：原 `qr.createImgTag()` 生成 GIF 格式二维码，微信扫一扫、iOS 相机等主流扫码器识别率极低。

**修复**：改用 Canvas 绘制二维码并导出为 PNG 格式（`canvas.toDataURL('image/png')`），所有扫码器通用识别。

### 2. 增加账号密码自动记忆功能

**功能**：登录页增加"记住账号密码"复选框，使用 `localStorage` 存储。下次打开登录页自动填充账号密码，焦点跳到密码框，直接点登录即可。

## License

MIT
