# SuXinLu Blog / 素心园

一个给妈妈使用的国风个人博客项目。

前台负责展示文章、阅读详情、点赞、留言；后台负责登录、草稿保存、文章发布、留言审核。视觉上强调宣纸、印章、水墨、留白，以及浅色荷塘 / 深色竹林的氛围切换。

- html静态演示地址：https://wep-56.github.io/SuXinLu-blog/
- 实机运行地址：https://suxinlu-blog-production.up.railway.app/
（账号：admin 密码：suchinlu2025 此为演示部署，不要上传任何隐私内容）

## 使用Railway一键部署
[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/aoXA0J?referralCode=bxT5D0&utm_medium=integration&utm_source=template&utm_campaign=generic)

## 技术栈

- 后端：`Flask`
- 数据库：`SQLite`
- 模板：`Jinja2`
- 前端：原生 `HTML + CSS + JavaScript`
- 媒体存储：本地文件目录 `static/uploads/`
- 静态演示页：原生 `HTML + CSS`
- GitHub Pages：从 `docs/` 目录部署

## 设计风格

- 主风格：古风、墨感、静气、低干扰
- 浅色模式：左右侧荷塘水墨点缀
- 深色模式：左右侧竹林水墨点缀
- 配色：宣纸底、墨色文字、竹青、印章红
- 阅读体验：大字号、较宽行距、卷轴式排版
- 后台体验：尽量直给，减少学习成本

## 当前功能

- 首页文章列表
- 文章详情页
- 点赞
- 留言提交
- 留言后台审核
- 后台登录
- 草稿保存
- 草稿列表 / 删除草稿 / 继续编辑
- 正文发布
- 已发布文章列表
- 已发布文章重新起草
- 按文章编号跳转
- 独立关于页
- 全局浅色 / 深色主题切换
- GitHub Pages 静态演示页

## 目录结构

```text
SuXinLu-blog/
├─ app.py
├─ requirements.txt
├─ readme.md
├─ .gitignore
├─ templates/
│  ├─ index.html
│  ├─ post.html
│  ├─ login.html
│  ├─ admin.html
│  ├─ creator.html
│  ├─ about.html
│  └─ _paintings.html
├─ static/
│  └─ uploads/
├─ docs/                        GitHub Pages 静态演示目录
│  ├─ index.html
│  ├─ Main-screen.html
│  ├─ blog-main.html
│  ├─ creator.html
│  └─ login.html
└─ 
```

## 本地开发运行

### 1. 安装 Python

建议使用 `Python 3.10+`。

### 2. 创建虚拟环境

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 启动项目

```bash
python app.py
```

默认地址：

- 首页：`http://127.0.0.1:5000/`
- 关于页：`http://127.0.0.1:5000/about`
- 登录页：`http://127.0.0.1:5000/login`

## 自行部署教程

下面这套流程适合自己放到云主机、轻量服务器、家用 Linux 主机，或者任意能跑 Python 的环境。

### 1. 上传项目

把整个项目目录上传到服务器，例如：

```bash
/opt/SuXinLu-blog
```

### 2. 创建虚拟环境并安装依赖

```bash
cd /opt/SuXinLu-blog
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. 设置环境变量

建议至少设置这三个：

```bash
export SECRET_KEY="请换成你自己的随机长字符串"
export ADMIN_USERNAME="admin"
export ADMIN_PASSWORD="请换成你自己的后台密码"
```

说明：

- `SECRET_KEY`：Flask 会话签名密钥，部署时必须改
- `ADMIN_USERNAME`：首次初始化数据库时创建的后台账号
- `ADMIN_PASSWORD`：首次初始化数据库时创建的后台密码

### 4. 启动服务

开发 / 自测：

```bash
python app.py
```

如果准备正式对外运行，建议使用真正的 WSGI 服务器，而不是 Flask 自带开发服务器。常见组合：

- Linux：`gunicorn + nginx`
- Windows：`waitress`

这个仓库当前提供的是开发运行方式，没有额外封装生产部署脚本。

### 5. 保留运行数据

部署时一定要持久化这两个位置：

- `blog.db`
- `static/uploads/`

否则文章、草稿、留言和封面图都会丢。

## 部署后需要修改的点

### 1. 后台账号和密码

优先通过环境变量控制：

```bash
ADMIN_USERNAME
ADMIN_PASSWORD
```

注意：

- 这两个值只会在数据库第一次初始化时写入
- 如果 `blog.db` 已经存在，再改环境变量不会自动覆盖旧账号密码

如果库已经生成，又要改密码，有两种方式：

1. 登录后台后在“账号设置”里改
2. 删除 `blog.db` 后重新初始化

### 2. SECRET_KEY

部署时必须改：

```bash
SECRET_KEY
```

不改的话，会话安全性不够。

### 3. 关于页链接

当前关于页链接在 [app.py](...\mom's blog\app.py) 的 `about()` 路由里定义：

- 小红书
- 微信公众号
- 微博
- 哔哩哔哩

把里面的 `url` 改成你自己的实际地址即可。

### 4. 诗词内容

首页和关于页的“案头一句”来自 [app.py](...\mom's blog\app.py) 里的 `QUOTES` 列表。

想增加随机诗句，直接往这个列表追加。

### 5. 博客标题 / 副标题 / 页面文案

在 `templates/` 目录对应页面中修改：

- `index.html`
- `post.html`
- `about.html`
- `creator.html`
- `admin.html`
- `login.html`

### 6. 上传存储方式

当前上传目录是：

```text
static/uploads/
```

如果以后要接对象存储、图床或 CDN，需要改 [app.py](C:\Users\14844\Downloads\mom's blog\app.py) 里的上传逻辑。

## GitHub Pages 说明

仓库已经准备好 `docs/` 目录用于静态演示页。

演示内容包括：

- `docs/Main-screen.html`
- `docs/blog-main.html`
- `docs/creator.html`
- `docs/login.html`

并且额外提供了一个演示入口页：

- `docs/index.html`

### Pages 部署方式

项目里会包含一个 GitHub Actions 工作流：

- `.github/workflows/pages.yml`

它会把 `docs/` 目录自动部署到 GitHub Pages。

### Pages 


```text
https://wep-56.github.io/SuXinLu-blog/
```



## 备注

- 根目录那几个 `.html` 主要是静态演示稿
- Flask 真正运行用的是 `templates/`
- 全局左右侧水墨背景统一收在 `templates/_paintings.html`
