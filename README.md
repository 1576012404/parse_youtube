# YouTube 博主每日更新追踪

自动追踪指定 YouTube 博主的每日更新，使用 AI 生成摘要并通过邮件或飞书发送通知。

## 功能

- 自动获取指定频道的最新视频
- 提取视频字幕内容
- 使用 AI (DeepSeek/OpenAI 兼容) 生成内容摘要
- 支持邮件通知
- 支持飞书机器人通知
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

在仓库的 **Settings → Secrets and variables → Actions** 中添加：

#### 必需配置

| Secret 名称 | 说明 |
|------------|------|
| `YOUTUBE_API_KEY` | YouTube Data API v3 Key |
| `LLM_API_KEY` | DeepSeek 或 OpenAI API Key |
| `NOTIFICATION_TYPE` | 通知类型: `email` / `feishu` / `both` |

#### LLM 配置（可选）

| Secret 名称 | 默认值 | 说明 |
|------------|--------|------|
| `LLM_BASE_URL` | `https://api.deepseek.com/v1` | API 地址 |
| `LLM_MODEL` | `deepseek-chat` | 模型名称 |

#### 邮件通知（NOTIFICATION_TYPE 为 email 或 both 时必需）

| Secret 名称 | 说明 |
|------------|------|
| `SMTP_SERVER` | SMTP 服务器地址 |
| `SMTP_PORT` | SMTP 端口 |
| `SENDER_EMAIL` | 发件人邮箱 |
| `SENDER_PASSWORD` | SMTP 授权码 |
| `RECEIVER_EMAIL` | 收件人邮箱 |

#### 飞书通知（NOTIFICATION_TYPE 为 feishu 或 both 时必需）

| Secret 名称 | 说明 |
|------------|------|
| `FEISHU_WEBHOOK` | 飞书机器人 Webhook 地址 |

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

### 飞书机器人 Webhook

1. 打开飞书群聊 → 设置 → 群机器人 → 添加机器人
2. 选择「自定义机器人」
3. 复制 Webhook 地址

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
