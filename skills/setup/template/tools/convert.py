#!/usr/bin/env python3
"""Turn a Claude or ChatGPT data export into readable files in sources/.

  convert.py list <export>                     every conversation: number, date, size, title
  convert.py extract <export> --ids 3,7,12     write the chosen conversations to sources/
  convert.py extract <export> --match word     ... every conversation with the word in its title
  convert.py extract <export> --since 2026-01-01
  convert.py extract <export> --all

<export> is the zip you downloaded, or the conversations.json inside it.
Runs entirely on this computer. Export formats change from time to time; if
this fails, paste the conversations into files in sources/ instead.
"""
import datetime as dt
import io
import json
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = os.path.join(ROOT, "sources")


def load(path):
    path = os.path.expanduser(path)
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if os.path.basename(n) == "conversations.json"]
            if not names:
                sys.exit("No conversations.json inside that zip.")
            with z.open(names[0]) as f:
                data = json.load(io.TextIOWrapper(f, encoding="utf-8"))
    else:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    if isinstance(data, dict):
        data = data.get("conversations") or list(data.values())
    return data


def when(value):
    if value in (None, ""):
        return None
    try:
        if isinstance(value, (int, float)):
            return dt.datetime.fromtimestamp(value, dt.timezone.utc).astimezone()
        return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone()
    except (ValueError, OSError, OverflowError):
        return None


def text_of(content):
    """Text from either export's message content, ignoring tool and image parts."""
    if isinstance(content, str):
        return content
    out = []
    if isinstance(content, dict):
        content = content.get("parts") or []
    for part in content or []:
        if isinstance(part, str):
            out.append(part)
        elif isinstance(part, dict) and part.get("type") in (None, "text") and part.get("text"):
            out.append(part["text"])
    return "\n\n".join(p for p in out if p.strip())


def claude_turns(conv):
    for m in conv.get("chat_messages") or []:
        body = text_of(m.get("content")) or (m.get("text") or "")
        who = "You" if m.get("sender") == "human" else "Assistant"
        if body.strip():
            yield who, when(m.get("created_at")), body.strip()


def chatgpt_turns(conv):
    mapping = conv.get("mapping") or {}
    chain, node = [], conv.get("current_node")
    while node and node in mapping:
        chain.append(mapping[node])
        node = mapping[node].get("parent")
    if not chain:
        chain = sorted(mapping.values(),
                       key=lambda n: ((n.get("message") or {}).get("create_time") or 0), reverse=True)
    for item in reversed(chain):
        m = item.get("message") or {}
        role = (m.get("author") or {}).get("role")
        if role not in ("user", "assistant"):
            continue
        body = text_of(m.get("content"))
        if body.strip():
            yield ("You" if role == "user" else "Assistant"), when(m.get("create_time")), body.strip()


def parse(data):
    convs = []
    for conv in data:
        if not isinstance(conv, dict):
            continue
        if "chat_messages" in conv:
            kind, title, turns = "claude", conv.get("name"), list(claude_turns(conv))
            started = when(conv.get("created_at"))
        elif "mapping" in conv:
            kind, title, turns = "chatgpt", conv.get("title"), list(chatgpt_turns(conv))
            started = when(conv.get("create_time"))
        else:
            continue
        if not turns:
            continue
        started = started or turns[0][1]
        convs.append({"kind": kind, "title": (title or "Untitled").strip(), "start": started, "turns": turns,
                      "words": sum(len(t[2].split()) for t in turns)})
    convs.sort(key=lambda c: c["start"] or dt.datetime.min.replace(tzinfo=dt.timezone.utc))
    return convs


def day(c):
    return f"{c['start']:%Y-%m-%d}" if c["start"] else "undated   "


def cmd_list(convs, _args):
    print(f"{'No.':>4}  {'Date':10}  {'Turns':>5}  {'Words':>7}  Title")
    for i, c in enumerate(convs, 1):
        print(f"{i:>4}  {day(c)}  {len(c['turns']):>5}  {c['words']:>7}  {c['title'][:70]}")
    print(f"\n{len(convs)} conversations, {sum(c['words'] for c in convs):,} words in all.")


def cmd_extract(convs, args):
    chosen = []
    if "--all" in args:
        chosen = list(enumerate(convs, 1))
    if "--ids" in args:
        ids = {int(x) for x in args[args.index("--ids") + 1].split(",") if x.strip()}
        chosen += [(i, c) for i, c in enumerate(convs, 1) if i in ids]
    if "--match" in args:
        word = args[args.index("--match") + 1].lower()
        chosen += [(i, c) for i, c in enumerate(convs, 1) if word in c["title"].lower()]
    if "--since" in args:
        since = args[args.index("--since") + 1]
        pool = chosen or list(enumerate(convs, 1))
        chosen = [(i, c) for i, c in pool if day(c) >= since]
    if not chosen:
        sys.exit("Nothing chosen. Use --ids, --match, --since or --all.")
    os.makedirs(SOURCES, exist_ok=True)
    total, done = 0, set()
    for i, c in chosen:
        if i in done:
            continue
        done.add(i)
        slug = re.sub(r"[^a-z0-9]+", "-", c["title"].lower()).strip("-")[:50] or "untitled"
        name = f"{day(c).strip()}-{i:04d}-{slug}.md"
        with open(os.path.join(SOURCES, name), "w", encoding="utf-8") as f:
            f.write(f"# {c['title']}\n\n")
            f.write(f"From a {c['kind']} export. Started {day(c).strip()}. {len(c['turns'])} turns.\n\n")
            for who, at, body in c["turns"]:
                stamp = f" ({at:%Y-%m-%d %H:%M})" if at else ""
                f.write(f"**{who}**{stamp}\n\n{body}\n\n---\n\n")
        total += c["words"]
        print(f"sources/{name}  ({c['words']:,} words)")
    print(f"\n{len(done)} conversations written, {total:,} words in all.")


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("list", "extract"):
        sys.exit(__doc__)
    conversations = parse(load(sys.argv[2]))
    {"list": cmd_list, "extract": cmd_extract}[sys.argv[1]](conversations, sys.argv[3:])
