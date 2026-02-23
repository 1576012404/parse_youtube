# YouTube 博主每日更新追踪

自动追踪指定 YouTube 博主的每日更新，生成摘要并发送邮件。

## 功能

- 自动获取指定频道的最新视频
- 提取视频字幕内容
- 使用 DeepSeek 生成内容摘要
- 通过邮件发送每日汇总

## 配置步骤

### 1. 获取 YouTube Data API Key

1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建新项目或选择现有项目
3. 启用 YouTube Data API v3
4. 创建 API 凭据（API Key）

### 2. 获取 DeepSeek API Key

访问 [DeepSeek 开放平台](https://platform.deepseek.com/) 注册并获取 API Key

### 3. 配置邮箱 SMTP（以 QQ 邮箱为例）

1. 登录 QQ 邮箱 → 设置 → 账户
2. 开启 POP3/SMTP 服务
3. 生成授权码（用于 SMTP 密码）

### 4. 查找频道 ID

在 YouTube 频道页面，查看源代码搜索 `channelId`，或使用 [Comment Picker](https://commentpicker.com/youtube-channel-id.php) 工具。

## 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 复制配置文件
cp config.example.json config.json

# 编辑 config.json，填入你的 API Key 和邮箱配置
# 编辑 channels.json，确认频道 ID 正确

# 运行
python main.py
```

## GitHub Actions 部署

### 1. Fork 本仓库

### 2. 配置 Secrets

在仓库的 Settings → Secrets and variables → Actions 中添加：

**CONFIG_JSON** - 完整的配置 JSON：
```json
{
  "youtube_api_key": "你的YouTube API Key",
  "deepseek_api_key": "你的DeepSeek API Key",
  "deepseek_base_url": "https://api.deepseek.com/v1",
  "email": {
    "smtp_server": "smtp.qq.com",
    "smtp_port": 587,
    "sender_email": "发件人邮箱",
    "sender_password": "SMTP授权码",
    "receiver_email": "收件人邮箱"
  }
}
```

### 3. 启用 Actions

进入 Actions 页面，启用 workflow。

定时任务会在每天北京时间 8:00 (UTC 0:00) 自动运行。

也可以手动触发：Actions → Daily YouTube Update → Run workflow

## 修改频道列表

编辑 `channels.json` 文件：

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

## 文件说明

| 文件 | 说明 |
|------|------|
| `main.py` | 主程序 |
| `channels.json` | 追踪的频道列表 |
| `config.json` | API 密钥和邮箱配置（需自行创建） |
| `config.example.json` | 配置模板 |
| `processed_videos.json` | 已处理视频记录 |
| `.github/workflows/daily.yml` | GitHub Actions 配置 |
