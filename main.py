import json
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

import requests
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

CONFIG_FILE = "config.json"
CHANNELS_FILE = "channels.json"
PROCESSED_FILE = "processed_videos.json"


def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_channels():
    with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)["channels"]


def load_processed_videos():
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_processed_videos(video_ids: set):
    with open(PROCESSED_FILE, "w", encoding="utf-8") as f:
        json.dump(list(video_ids), f)


def get_latest_videos(api_key: str, channel_id: str, max_results: int = 5):
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "key": api_key,
        "channelId": channel_id,
        "part": "snippet",
        "order": "date",
        "maxResults": max_results,
        "type": "video",
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json().get("items", [])


def get_video_transcript(video_id: str, languages: list = ["zh-Hans", "zh-Hant", "zh-CN", "zh-TW", "en"]) -> Optional[str]:
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        try:
            transcript = transcript_list.find_transcript(languages)
        except NoTranscriptFound:
            transcript = transcript_list.find_generated_transcript(languages)
        transcript_data = transcript.fetch()
        return " ".join([entry["text"] for entry in transcript_data])
    except (TranscriptsDisabled, NoTranscriptFound, Exception) as e:
        print(f"无法获取视频 {video_id} 的字幕: {e}")
        return None


def transcribe_with_whisper(api_key: str, video_url: str) -> Optional[str]:
    print(f"使用 Whisper 转写: {video_url} (需要先下载音频)")
    return None


def summarize_with_deepseek(api_key: str, base_url: str, text: str, video_title: str) -> str:
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
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
    )
    return response.choices[0].message.content


def send_email(config: dict, subject: str, body: str):
    email_config = config["email"]
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = email_config["sender_email"]
    msg["To"] = email_config["receiver_email"]

    html_content = body.replace("\n", "<br>")
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    with smtplib.SMTP(email_config["smtp_server"], email_config["smtp_port"]) as server:
        server.starttls()
        server.login(email_config["sender_email"], email_config["sender_password"])
        server.sendmail(
            email_config["sender_email"],
            email_config["receiver_email"],
            msg.as_string(),
        )


def main():
    print(f"开始执行 - {datetime.now()}")
    config = load_config()
    channels = load_channels()
    processed = load_processed_videos()

    api_key = config["youtube_api_key"]
    deepseek_key = config["deepseek_api_key"]
    deepseek_url = config.get("deepseek_base_url", "https://api.deepseek.com/v1")

    new_summaries = []

    for channel in channels:
        channel_name = channel["name"]
        channel_id = channel["channel_id"]
        print(f"\n检查频道: {channel_name}")

        try:
            videos = get_latest_videos(api_key, channel_id, max_results=3)
        except Exception as e:
            print(f"获取频道视频失败: {e}")
            continue

        for video in videos:
            video_id = video["id"]["videoId"]
            title = video["snippet"]["title"]
            published = video["snippet"]["publishedAt"]

            if video_id in processed:
                print(f"  跳过已处理: {title}")
                continue

            print(f"  处理新视频: {title}")

            transcript = get_video_transcript(video_id)
            if not transcript:
                print(f"  无法获取字幕，跳过")
                continue

            try:
                summary = summarize_with_deepseek(deepseek_key, deepseek_url, transcript, title)
            except Exception as e:
                print(f"  生成摘要失败: {e}")
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

    save_processed_videos(processed)

    if new_summaries:
        today = datetime.now().strftime("%Y-%m-%d")
        subject = f"YouTube博主每日更新汇总 - {today}"
        
        body_parts = [f"<h1>YouTube博主每日更新汇总</h1>", f"<p>日期: {today}</p><hr>"]
        
        for item in new_summaries:
            body_parts.append(f"""
<h2>{item['title']}</h2>
<p><b>频道:</b> {item['channel']} | <a href="{item['url']}">观看视频</a></p>
<h3>内容摘要:</h3>
<p>{item['summary']}</p>
<hr>
""")
        
        body = "".join(body_parts)
        
        try:
            send_email(config, subject, body)
            print(f"\n邮件发送成功，共 {len(new_summaries)} 条新视频")
        except Exception as e:
            print(f"\n邮件发送失败: {e}")
    else:
        print("\n今天没有新视频更新")

    print(f"执行完成 - {datetime.now()}")


if __name__ == "__main__":
    main()
