import json

CHANNELS_FILE = "channels.json"


def load_channels():
    try:
        with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            channels = data.get("channels", [])
            clean = []
            for ch in channels:
                if isinstance(ch, dict) and "id" in ch and "title" in ch:
                    clean.append(ch)
            return clean
    except Exception:
        return []


def save_channels(channels):
    with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
        json.dump({"channels": channels}, f, ensure_ascii=False, indent=2)


def add_channel(ch_id, title):
    ch_id = str(ch_id)
    channels = load_channels()
    for ch in channels:
        if ch["id"] == ch_id:
            return
    channels.append({"id": ch_id, "title": title})
    save_channels(channels)


def remove_channel(ch_id):
    ch_id = str(ch_id)
    channels = load_channels()
    channels = [c for c in channels if c["id"] != ch_id]
    save_channels(channels)


def get_channel(ch_id):
    ch_id = str(ch_id)
    for ch in load_channels():
        if ch["id"] == ch_id:
            return ch
    return None
