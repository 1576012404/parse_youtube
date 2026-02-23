# YouTube 博主每日更新追踪

自动追踪指定 YouTube 博主的每日更新，使用 AI 生成摘要并通过邮件发送。

## 功能

- 自动获取指定频道的最新视频
- 提取视频字幕内容
- 使用 AI (DeepSeek/OpenAI 兼容) 生成内容摘要
- 通过邮件发送每日汇总
- 支持 GitHub Actions 定时执行

## 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 复制环境变量模板
cp .env.example .env

# 编辑 .env 填入配置
# 编辑 channels.json 确认频道 ID

# 运行
python main.py
```

## GitHub Actions 部署

### 1. Fork 本仓库

### 2. 配置 Secrets

在仓库的 **Settings → Secrets and variables → Actions** 中添加以下 secrets：

| Secret 名称 | 必需 | 说明 |
|------------|------|------|
| `YOUTUBE_API_KEY` | ✅ | YouTube Data API v3 Key |
| `LLM_API_KEY` | ✅ | DeepSeek 或 OpenAI API Key |
| `LLM_BASE_URL` | ❌ | API 地址，默认 DeepSeek |
| `LLM_MODEL` | ❌ | 模型名称，默认 deepseek-chat |
| `SMTP_SERVER` | ❌ | SMTP 服务器地址 |
| `SMTP_PORT` | ❌ | SMTP 端口，默认 587 |
| `SENDER_EMAIL` | ❌ | 发件人邮箱 |
| `SENDER_PASSWORD` | ❌ | SMTP 授权码/密码 |
| `RECEIVER_EMAIL` | ❌ | 收件人邮箱 |

> 邮件配置为可选，不配置则只生成摘要不发送邮件。

### 3. 启用 Actions

进入 Actions 页面启用 workflow。

- 定时任务：每天 UTC 0:00（北京时间 8:00）自动运行
- 手动触发：Actions → Daily YouTube Update → Run workflow

## 获取 API Key

### YouTube Data API Key

1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建项目 → 启用 YouTube Data API v3
3. 创建凭据 → API Key

### DeepSeek API Key

访问 [DeepSeek 开放平台](https://platform.deepseek.com/) 注册获取

### 邮箱 SMTP（QQ邮箱）

1. 登录 QQ 邮箱 → 设置 → 账户
2. 开启 POP3/SMTP 服务
3. 生成授权码

### 查找频道 ID

在频道页面查看源码搜索 `channelId`，或使用 [Comment Picker](https://commentpicker.com/youtube-channel-id.php)

## 修改频道列表

编辑 `channels.json`：

```json
{
  "channels": [
    {
      "name": "频道名称",
      "channel_id": "UCxxxxxx"
    }
  ]
}
```

## 项目结构

```
.
├── main.py                 # 主程序
├── channels.json           # 频道列表
├── processed_videos.json   # 已处理视频（自动生成）
├── requirements.txt        # 依赖
├── pyproject.toml          # 项目配置
├── .env.example            # 环境变量模板
└── .github/workflows/
    └── daily.yml           # GitHub Actions 配置
```
