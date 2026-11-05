# YouTube Discord Notifier
A lightweight YouTube monitor that sends automatic notifications to Discord whenever your selected YouTube channels upload a video or start a live stream.

## How to use:

### YouTube API setting [Google Cloud Console](https://console.cloud.google.com/)
```text
1. setting YouTube API in Google Cloud Console
2. create new project or select your existing project
3. enable YouTube Data API v3
4. create API Key
5. copy API Key[1]
```

### Create Discord Webhook
```text
1. choose your server on discord
2. go to Edit Channel
3. go to Integrations
4. create new Webhook
5. copy Webhook URL[2]
```

### GitHub Repository Secrets 
```text
1. in this Repository, go to Settings → Secrets and variables → Actions → New repository secret
2. create Secrets following this pattern
YouTube_API_KEY: YouTube API Key[1]
DISCORD_WEBHOOK_A: Discord Webhook[2]
DISCORD_WEBHOOK_B: Discord Webhook(optional)
DISCORD_WEBHOOK_ERROR: Discord Webhook for system error alerts (optional, fallback to Group A)
```

if you want to get notifications in multiple discord channels, you can add more than two discord webhook

> ⚠️ Do not share your API Key or Webhook URLs publicly.

### Adding YouTube Channels
1. in `config.json` place the YouTube Channel ID[3] in "id"

example: 
```json
{
  "groups": {
    "A": {
      "webhook_env": "DISCORD_WEBHOOK_GROUP_A"
    },
    "B": {
      "webhook_env": "DISCORD_WEBHOOK_GROUP_B"
    }
  },
  "channels": [
    {
      "name": "Channel Name A",
      "id": "UCxxxxxxxxxxxxxxxxxxxxxx",
      "group": "A"
    },
    {
      "name": "Channel Name B",
      "id": "UCyyyyyyyyyyyyyyyyyyyyyy",
      "group": "B"
    }
  ]
}
```
[3] YouTube Channel ID can be get by go to the YouTube Channel you want to select, then right click and go to View page source. Press Ctrl+F and put in "channel_id". Copy the ID which always start with UC... ,that's the YouTube Channel ID

Example:
```json
{
  "name": "Example Channel",
  "id": "UCxxxxxxxxxxxxxxxx",
  "group": "A"
}
```
*This project is limited to a maximum of **30-ish** channels for optimal system effectiveness.

### cron-job setting [cron-job](https://console.cron-job.org/)

1. go to cron-job and create new cronjob
2. use this following setting:

```text
COMMON:
URL: https://api.github.com/repos/YOUR_USERNAME/YOUR_REPO/dispatches > change YOUR_USERNAME/YOUR_REPO to your own
Execution schedule: Every 5 minutes
```

```text
ADVANCED:
Headers [1], [2], [3]:

[1] Authorization: Bearer (Personal Access Token)

create your Personal Access Token (PAT): 
method 1: Fine-grained Token (Recommended for higher security)
1) go to Settings on your GitHub
2) Developer Settings > Personal access tokens > Fine-grained tokens, then create the token
Add permissions > Actions > Read and write > Generate token. when finished, copy the token
(starts with github_pat_...) then paste in Header Authorization: Bearer [token]

method 2: Classic Token (Easy to set up, with no sub-permission restrictions)
1) go to Settings on your GitHub
2) Developer Settings > Personal access tokens > Tokens(classic) > Generate new token > Generate new token(classic) > Check the box for the repo > Generate token
when finished, copy the token (starts with ghp_...) then paste in Header Authorization: Bearer [token]

[2] Accept: application/vnd.github.v3+json

[3] User-Agent: cron-job.org (or cron-job-bot)

Request method: POST

Request Body (JSON):

{
  "event_type": "cron_trigger"
}
```
--------------------

## Test Run
after finished cron-job setting, click Save then Test run

you can check the Workflow progress in the Actions tab in your Repository on GitHub which will automatically check for new videos and live streams every 5 minutes.

--------------------

### ₊⊹ Default Notifications Pattern

> YouTube Notifications

for New Videos:
```text
NEW VIDEO!! (x minutes ago)
{video link}
```

for Live Streams:
```text
NEW LIVE STREAM!! (x minutes ago)
{live stream link}
```


> System Notifications

for System Errors:
```text
[System Alert] YouTube Discord Notifier Error! (Timestamp)

Issue Found:
{error_message}
```

for System Recovery:
```text
[System Status] YouTube Monitor Notifier is back to normal. (Timestamp)

Resolved Issue:
{previous_error_message}
```

You can customize YouTube notification formats in `monitor.py`:

```python
def send_discord(webhook, video_id, event_type, group):
    video_url = f"https://www.YouTube.com/watch?v={video_id}"

    # Group A notification
    if group == "A":
        if event_type == "live":
            message = (
                "NEW LIVE STREAM!!\n" # EDIT HERE
                f"{video_url}"
            )
        else:
            message = (
                "NEW VIDEO!!\n" # EDIT HERE
                f"{video_url}"
            )
```
----------
### And why do I need to use this project?

Answer:
> No Subscription Required: You can still receive notifications directly through your Discord server from any YouTube channels even if you haven’t subscribed or aren't logged into your YouTube account on your device.

> Flexible Channel Categorization:: You can freely categorize your notifications by selecting various YouTube channels and configuring the bot to send alerts to specific channels of your choice on your Discord server.
- For example, route cooking content to #food and self-improvement content to #growth. You can also use this as a way to share updates and discuss new videos with your friends on your Discord server.

> Automation for Creators: If you are a YouTuber or content creator with a Discord server for your followers, you can leverage this project to automatically send notifications to your server. This ensures your fans never miss a new video, saving you the time and effort of having to post an announcement on Discord yourself every single time.

> No more issue when YouTube fails to send notifications for new video uploads or live streams to subscribers.

> And last but not least, this project is available for use at **no cost**.

*THANK YOU*

****Disclaimer: This project was developed with the assistance of AI.****

```text
Developer
- SealwingsZ
```
:3
