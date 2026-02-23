import json
import logging
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

CHANNELS_FILE = os.getenv("CHANNELS_FILE", "channels.json")
PROCESSED_FILE = os.getenv("PROCESSED_FILE", "processed_videos.json")


class Config:
    def __init__(self):
        self.youtube_api_key = self._get_required("YOUTUBE_API_KEY")
        self.llm_api_key = self._get_required("LLM_API_KEY")
        self.llm_base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
        self.llm_model = os.getenv("LLM_MODEL", "deepseek-chat")
        
        self.notification_type = os.getenv("NOTIFICATION_TYPE", "email").lower()
        
        self.smtp_server = os.getenv("SMTP_SERVER", "")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.sender_email = os.getenv("SENDER_EMAIL", "")
        self.sender_password = os.getenv("SENDER_PASSWORD", "")
        self.receiver_email = os.getenv("RECEIVER_EMAIL", "")
        
        self.feishu_webhook = os.getenv("FEISHU_WEBHOOK", "")
        
        self._validate()
    
    def _get_required(self, key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Required environment variable {key} is not set")
        return value
    
    def _validate(self) -> None:
        if self.notification_type not in ("email", "feishu", "both"):
            raise ValueError(f"NOTIFICATION_TYPE must be 'email', 'feishu', or 'both', got '{self.notification_type}'")
        
        if self.notification_type in ("email", "both"):
            if not all([self.smtp_server, self.sender_email, self.sender_password, self.receiver_email]):
                raise ValueError("Email notification requires SMTP_SERVER, SENDER_EMAIL, SENDER_PASSWORD, and RECEIVER_EMAIL")
        
        if self.notification_type in ("feishu", "both"):
            if not self.feishu_webhook:
                raise ValueError("Feishu notification requires FEISHU_WEBHOOK")
    
    @property
    def email_enabled(self) -> bool:
        return self.notification_type in ("email", "both")
    
    @property
    def feishu_enabled(self) -> bool:
        return self.notification_type in ("feishu", "both")


def load_channels() -> list[dict]:
    with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("channels", [])


def load_processed_videos() -> set[str]:
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_processed_videos(video_ids: set[str]) -> None:
    with open(PROCESSED_FILE, "w", encoding="utf-8") as f:
        json.dump(list(video_ids), f, ensure_ascii=False, indent=2)


def get_latest_videos(api_key: str, channel_id: str, max_results: int = 5) -> list[dict]:
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "key": api_key,
        "channelId": channel_id,
        "part": "snippet",
        "order": "date",
        "maxResults": max_results,
        "type": "video",
    }
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json().get("items", [])


def get_video_transcript(
    video_id: str,
    languages: Optional[list[str]] = None
) -> Optional[str]:
    if languages is None:
        languages = ["zh-Hans", "zh-Hant", "zh-CN", "zh-TW", "en"]
    
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        try:
            transcript = transcript_list.find_transcript(languages)
        except NoTranscriptFound:
            transcript = transcript_list.find_generated_transcript(languages)
        transcript_data = transcript.fetch()
        return " ".join([entry["text"] for entry in transcript_data])
    except (TranscriptsDisabled, NoTranscriptFound) as e:
        logger.warning(f"No transcript available for video {video_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error fetching transcript for video {video_id}: {e}")
        return None


def summarize_content(
    api_key: str,
    base_url: str,
    text: str,
    video_title: str,
    model: str = "deepseek-chat"
) -> str:
    client = OpenAI(api_key=api_key, base_url=base_url)
    
    prompt = f"""请总结以下YouTube视频的内容，提取关键信息和要点。

视频标题: {video_title}

视频字幕内容:
{text[:8000]}

请用中文输出:
1. 核心主题 (一句话概括)
2. 主要观点 (3-5个要点)
3. 重要结论或建议

保持简洁，总字数不超过300字。"""

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
    )
    return response.choices[0].message.content or ""


def send_email(
    config: Config,
    subject: str,
    body: str
) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config.sender_email
    msg["To"] = config.receiver_email
    msg.attach(MIMEText(body, "html", "utf-8"))

    with smtplib.SMTP(config.smtp_server, config.smtp_port) as server:
        server.starttls()
        server.login(config.sender_email, config.sender_password)
        server.sendmail(config.sender_email, config.receiver_email, msg.as_string())


def send_feishu(config: Config, summaries: list[dict], date_str: str) -> None:
    content_lines = [f"## YouTube 每日更新汇总 - {date_str}\n"]
    
    for item in summaries:
        content_lines.append(f"### [{item['title']}]({item['url']})")
        content_lines.append(f"**频道:** {item['channel']}")
        content_lines.append(f"**摘要:**\n{item['summary']}")
        content_lines.append("---\n")
    
    content = "\n".join(content_lines)
    
    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"YouTube 每日更新汇总 - {date_str}"
                },
                "template": "blue"
            },
            "elements": []
        }
    }
    
    for item in summaries:
        payload["card"]["elements"].extend([
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**[{item['title']}]({item['url']})**\n频道: {item['channel']}"
                }
            },
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": item['summary'].replace("\n", "\n")
                }
            },
            {
                "tag": "hr"
            }
        ])
    
    if payload["card"]["elements"]:
        payload["card"]["elements"].pop()
    
    response = requests.post(
        config.feishu_webhook,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=30
    )
    response.raise_for_status()
    result = response.json()
    if result.get("code", 0) != 0:
        raise Exception(f"Feishu API error: {result}")


def format_email_body(summaries: list[dict], date_str: str) -> str:
    body_parts = [
        "<!DOCTYPE html>",
        "<html><head><meta charset='utf-8'></head><body>",
        f"<h1>YouTube 每日更新汇总</h1>",
        f"<p>日期: {date_str}</p><hr>",
    ]
    
    for item in summaries:
        body_parts.append(f"""
<div style="margin-bottom: 30px;">
    <h2 style="color: #cc0000;"><a href="{item['url']}">{item['title']}</a></h2>
    <p><b>频道:</b> {item['channel']}</p>
    <h3>内容摘要:</h3>
    <div style="background: #f5f5f5; padding: 15px; border-radius: 5px;">
        {item['summary'].replace(chr(10), '<br>')}
    </div>
</div>
<hr>
""")
    
    body_parts.append("</body></html>")
    return "".join(body_parts)


def send_notifications(config: Config, summaries: list[dict]) -> None:
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    if config.email_enabled:
        try:
            subject = f"YouTube 每日更新汇总 - {date_str}"
            body = format_email_body(summaries, date_str)
            send_email(config, subject, body)
            logger.info(f"Email sent successfully with {len(summaries)} new videos")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
    
    if config.feishu_enabled:
        try:
            send_feishu(config, summaries, date_str)
            logger.info(f"Feishu notification sent successfully with {len(summaries)} new videos")
        except Exception as e:
            logger.error(f"Failed to send Feishu notification: {e}")


def main() -> None:
    logger.info(f"Starting YouTube channel monitor - {datetime.now()}")
    
    try:
        config = Config()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return
    
    channels = load_channels()
    processed = load_processed_videos()
    
    logger.info(f"Monitoring {len(channels)} channels, {len(processed)} videos already processed")
    logger.info(f"Notification type: {config.notification_type}")
    
    new_summaries = []
    
    for channel in channels:
        channel_name = channel.get("name", "Unknown")
        channel_id = channel.get("channel_id")
        
        if not channel_id:
            logger.warning(f"Skipping channel {channel_name}: no channel_id")
            continue
            
        logger.info(f"Checking channel: {channel_name}")
        
        try:
            videos = get_latest_videos(config.youtube_api_key, channel_id, max_results=3)
        except Exception as e:
            logger.error(f"Failed to fetch videos from {channel_name}: {e}")
            continue
        
        for video in videos:
            video_id = video.get("id", {}).get("videoId")
            if not video_id:
                continue
                
            snippet = video.get("snippet", {})
            title = snippet.get("title", "Untitled")
            published = snippet.get("publishedAt", "")
            
            if video_id in processed:
                logger.info(f"  Skipping processed: {title}")
                continue
            
            logger.info(f"  Processing: {title}")
            
            transcript = get_video_transcript(video_id)
            if not transcript:
                logger.warning(f"  No transcript, skipping")
                processed.add(video_id)
                continue
            
            try:
                summary = summarize_content(
                    config.llm_api_key,
                    config.llm_base_url,
                    transcript,
                    title,
                    config.llm_model
                )
            except Exception as e:
                logger.error(f"  Failed to summarize: {e}")
                continue
            
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            new_summaries.append({
                "channel": channel_name,
                "title": title,
                "url": video_url,
                "published": published,
                "summary": summary,
            })
            
            processed.add(video_id)
            logger.info(f"  Summary generated successfully")
    
    save_processed_videos(processed)
    
    if new_summaries:
        send_notifications(config, new_summaries)
    else:
        logger.info("No new videos found today")
    
    logger.info(f"Completed - {datetime.now()}")


if __name__ == "__main__":
    main()
