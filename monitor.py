import os
import json
import requests
from datetime import datetime, timezone
from pathlib import Path
import time

# -------------------------
# CONFIG
# -------------------------
API_KEY = os.environ["YOUTUBE_API_KEY"]
CONFIG_FILE, STATE_FILE = "config.json", "state.json"
BASE_URL = "https://www.googleapis.com/youtube/v3"

session = requests.Session()


def api_get(endpoint, params):
    params["key"] = API_KEY
    response = session.get(f"{BASE_URL}/{endpoint}", params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def load_json(path, default):
    p = Path(path)
    return json.loads(p.read_text("utf-8")) if p.exists() else default


def save_state(state):
    Path(STATE_FILE).write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


# -------------------------
# ERROR & RECOVERY SYSTEM
# -------------------------
def should_send_error_alert(state, error_msg):
    """ตรวจสอบ Cooldown 6 ชั่วโมง (21,600 วินาที) สำหรับ Error ข้อความเดิม"""
    last_error = state.get("last_error")
    last_error_time = state.get("last_error_time")

    if last_error != error_msg or not last_error_time:
        return True

    last_time = datetime.fromisoformat(last_error_time)
    now = datetime.now(timezone.utc)
    return (now - last_time).total_seconds() >= 21600


def handle_error(state, error_msg, webhook):
    """จัดการส่งแจ้งเตือน Error เข้า Discord พร้อมบันทึก Cooldown ลง state"""
    if not webhook:
        print(f"Cannot send error alert: Webhook missing. Error: {error_msg}")
        return

    if should_send_error_alert(state, error_msg):
        now_ts = int(datetime.now(timezone.utc).timestamp())
        payload = {
            "content": (
                f"> **[System Alert] YouTube Discord Notifier Error!** (<t:{now_ts}:F> - <t:{now_ts}:R>)\n"
                f"\n"
                f"**Issue Detected:**\n"
                f"```{error_msg}```"
            ),
            "allowed_mentions": {"parse": []}
        }
        try:
            requests.post(webhook, json=payload, timeout=10)
            print("Sent error alert to Discord.")
        except Exception as e:
            print(f"Failed to send error alert to Discord: {e}")

        state["last_error"] = error_msg
        state["last_error_time"] = datetime.now(timezone.utc).isoformat()
        save_state(state)
    else:
        print(f"Skipped error alert (Cooldown active): {error_msg}")


def send_recovery_alert(webhook, last_error):
    """ส่งแจ้งเตือนเมื่อระบบกลับมาทำงานเป็นปกติหลังเกิด Error"""
    if not webhook:
        return

    now_ts = int(datetime.now(timezone.utc).timestamp())
    payload = {
        "content": (
            f"> **[System Status] YouTube Discord Notifier is back to normal.** (<t:{now_ts}:F> - <t:{now_ts}:R>)\n"
            f"\n"
            f"**Resolved Issue:**\n"
            f"```{last_error}```"
        ),
        "allowed_mentions": {"parse": []}
    }
    try:
        requests.post(webhook, json=payload, timeout=10)
        print("Sent recovery alert to Discord.")
    except Exception as e:
        print(f"Failed to send recovery alert to Discord: {e}")


# -------------------------
# YOUTUBE (Official API)
# -------------------------
def get_channel_videos_api(channel_id):
    cid = channel_id.strip()
    playlist_id = "UU" + cid[2:] if cid.startswith("UC") else cid

    data = api_get("playlistItems", {
        "part": "snippet",
        "playlistId": playlist_id,
        "maxResults": 3
    })
    
    return [item["snippet"]["resourceId"]["videoId"] for item in data.get("items", [])]


def get_video_details(video_ids):
    result = {}
    for start in range(0, len(video_ids), 50):
        batch = video_ids[start:start + 50]
        if batch:
            data = api_get("videos", {"part": "snippet,liveStreamingDetails", "id": ",".join(batch)})
            for video in data.get("items", []):
                result[video["id"]] = video
    return result


# -------------------------
# DISCORD
# -------------------------
def send_discord(webhook, video_id, event_type, group, event_time_iso=None):
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    time_tag = ""
    if event_time_iso:
        dt = datetime.fromisoformat(event_time_iso.replace("Z", "+00:00"))
        unix_ts = int(dt.timestamp())
        time_tag = f" (<t:{unix_ts}:R>)"

    if group == "A":
        if event_type == "live":
            message = f"NEW LIVE STREAM!!{time_tag}\n\n{video_url}"
        else:
            message = f"NEW VIDEO!!{time_tag}\n\n{video_url}"
    elif group == "B":
        if event_type == "live":
            message = f"NEW LIVE STREAM!!{time_tag}\n\n{video_url}"
        else:
            message = f"NEW VIDEO!!{time_tag}\n\n{video_url}"

    payload = {
        "content": message,
        "allowed_mentions": {"parse": []}
    }

    requests.post(webhook, json=payload, timeout=15).raise_for_status()
    time.sleep(1)
    print(f"Sent {event_type} notification to Group {group}: {video_id}")


# -------------------------
# MAIN MONITOR
# -------------------------
def main():
    config = load_json(CONFIG_FILE, {})
    state = load_json(STATE_FILE, {"last_run": None, "channels": {}})
    error_webhook = os.environ.get("DISCORD_WEBHOOK_ERROR") or os.environ.get("DISCORD_WEBHOOK_A")

    try:
        now = datetime.now(timezone.utc)
        groups, channels = config["groups"], config["channels"]
        all_video_ids, channel_videos, failed_channels = [], {}, set()
        state_changed = False

        # 1. Collect latest videos via YouTube Data API
        for channel in channels:
            try:
                ids = get_channel_videos_api(channel["id"])
                channel_videos[channel["id"]] = ids
                all_video_ids.extend(ids)
                print(f"Checked: {channel['name']} ({len(ids)} videos)")
            except Exception as error:
                failed_channels.add(channel["id"])
                print(f"Channel error: {channel['name']}: {error}")

        # 2. Get video and live details
        unique_ids = list(dict.fromkeys(all_video_ids))
        details = get_video_details(unique_ids) if unique_ids else {}

        # 3. Process each channel
        for channel in channels:
            channel_id = channel["id"]
            if channel_id in failed_channels:
                continue

            ids = channel_videos.get(channel_id, [])
            channel_state = state.get("channels", {}).get(channel_id)

            # First run for a channel
            if channel_state is None:
                live_ids = [
                    vid for vid in ids
                    if details.get(vid, {}).get("snippet", {}).get("liveBroadcastContent") == "live"
                ]
                state["channels"][channel_id] = {"seen": ids, "live_notified": live_ids}
                state_changed = True
                print(f"Initialized: {channel['name']}")
                continue

            seen = list(channel_state.get("seen", []))
            live_notified = list(channel_state.get("live_notified", []))
            webhook = os.environ[groups[channel["group"]]["webhook_env"]]

            for video_id in ids:
                video = details.get(video_id)
                if video is None:
                    continue

                snippet = video["snippet"]
                broadcast = snippet.get("liveBroadcastContent", "none")
                live_details = video.get("liveStreamingDetails")

                if broadcast == "live":
                    event_time = (live_details.get("actualStartTime") if live_details else None) or snippet.get("publishedAt")
                    if video_id not in live_notified:
                        send_discord(webhook, video_id, "live", channel["group"], event_time)
                        live_notified.append(video_id)
                        state_changed = True

                elif video_id not in seen and broadcast == "none" and live_details is None:
                    event_time = snippet.get("publishedAt")
                    send_discord(webhook, video_id, "video", channel["group"], event_time)

                if video_id not in seen:
                    seen.append(video_id)
                    state_changed = True

            channel_state["seen"] = seen[-10:]
            channel_state["live_notified"] = live_notified[-10:]

        # 4. Clear Error on Success
        if "last_error" in state:
            previous_error = state.get("last_error", "Unknown error")
            send_recovery_alert(error_webhook, previous_error)

            del state["last_error"]
            if "last_error_time" in state:
                del state["last_error_time"]
            state_changed = True
            print("Previous error cleared as run succeeded.")

        # 5. Save state
        if state_changed:
            state["last_run"] = now.isoformat()
            save_state(state)
            print("State updated and saved.")
        else:
            print("No new updates. Skipping state save.")

        if failed_channels:
            print("Some channels failed. Retrying next run.")

        print("Monitor completed.")

    except Exception as error:
        error_msg = str(error)
        print(f"Monitor failed with error: {error_msg}")
        handle_error(state, error_msg, error_webhook)
        raise error


if __name__ == "__main__":
    main()