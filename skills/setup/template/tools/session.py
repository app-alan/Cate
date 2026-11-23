#!/usr/bin/env python3
"""Session clock, word-for-word transcript export, and backup for a Cate folder.

  session.py open [--at HH:MM]   start a session; the clock runs from --at
                                 (the booked time) or from now
  session.py time                minutes used and left in the current session
  session.py tick                the same, but silent when no session is open
                                 (this is what the prompt hook runs)
  session.py next                the next booked slots
  session.py export [ID]         write the word-for-word transcript of a session
  session.py close               export, commit to the local repo, back up
  session.py backup              copy the folder to the backup folder, if one is set

Nothing here sends anything anywhere. The only copy it makes is to the backup
folder named in .cate/config.json, and only if you set one.
"""
import datetime as dt
import glob
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSIONS = os.path.join(ROOT, "sessions")
CURRENT = os.path.join(SESSIONS, ".current.json")
CONFIG = os.path.join(ROOT, ".cate", "config.json")
TOKEN = "CATE-SESSION-TOKEN"
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def config():
    cfg = {"name": "", "session_minutes": 50, "warn_minutes": 45, "slots": [], "backup_dir": ""}
    try:
        with open(CONFIG, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except (OSError, ValueError):
        pass
    return cfg


def now():
    return dt.datetime.now().astimezone()


def load_current(quiet=False):
    if not os.path.exists(CURRENT):
        if quiet:
            sys.exit(0)
        sys.exit("No session is open. Run: session.py open")
    with open(CURRENT, encoding="utf-8") as f:
        cur = json.load(f)
    cur["start_dt"] = dt.datetime.fromisoformat(cur["start"])
    return cur


def cmd_open(args):
    cfg = config()
    length = int(cfg["session_minutes"])
    os.makedirs(SESSIONS, exist_ok=True)
    t = now()
    if os.path.exists(CURRENT):
        with open(CURRENT, encoding="utf-8") as f:
            cur = json.load(f)
        age_h = (t - dt.datetime.fromisoformat(cur["start"])).total_seconds() / 3600
        if age_h < 3:
            sys.exit(
                f"A SESSION IS ALREADY OPEN: {cur['id']}, started {cur['start'][11:16]}, "
                "in another chat. Do not open a second one. Continue in that chat."
            )
    start = t
    if "--at" in args:
        hh, mm = args[args.index("--at") + 1].split(":")
        start = t.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
    existing = sorted(glob.glob(os.path.join(SESSIONS, "*-notes.md")))
    number = len(existing) + 1
    sid = f"{start:%Y-%m-%d}-{number:02d}"
    with open(CURRENT, "w", encoding="utf-8") as f:
        json.dump({"id": sid, "number": number, "start": start.isoformat()}, f)
    end = start + dt.timedelta(minutes=length)
    print(f"{TOKEN} {sid}")
    print(f"Session {number}. Booked start {start:%H:%M}, ends {end:%H:%M} ({start:%A %d %B %Y}).")
    late = int((t - start).total_seconds() // 60)
    if late > 0:
        print(f"It is now {t:%H:%M}: {late} minutes of the session have already gone.")
    print(f"Notes file: sessions/{sid}-notes.md")


def cmd_time(_args, quiet=False):
    cur = load_current(quiet)
    cfg = config()
    length, warn = int(cfg["session_minutes"]), int(cfg["warn_minutes"])
    t = now()
    used = (t - cur["start_dt"]).total_seconds() / 60
    left = length - used
    end = cur["start_dt"] + dt.timedelta(minutes=length)
    print(f"Now {t:%H:%M}. Session {cur['id']}: {used:.0f} min used, {left:.0f} min left, ends {end:%H:%M}.")
    if left <= 0:
        print("TIME IS UP. Close the session now.")
    elif used >= warn:
        print(f"LAST {length - warn} MINUTES. Start closing: summary, between-session work, next session.")


def cmd_tick(args):
    cmd_time(args, quiet=True)


def cmd_next(_args):
    slots = config()["slots"]
    if not slots:
        sys.exit("No slots are booked in .cate/config.json.")
    t = now()
    upcoming = []
    for offset in range(0, 15):
        day = t + dt.timedelta(days=offset)
        for slot in slots:
            if DAYS.index(str(slot["day"]).lower()[:3]) != day.weekday():
                continue
            hh, mm = str(slot["time"]).split(":")
            when = day.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
            if when > t:
                upcoming.append(when)
    for when in sorted(upcoming)[:3]:
        print(f"{when:%A %d %B %Y at %H:%M}")


def strip_noise(text):
    text = re.sub(r"<system-reminder>.*?</system-reminder>", "", text, flags=re.S)
    text = re.sub(r"</?pasted_content[^>]*>", "", text)
    text = re.sub(r"<(command-[a-z]+|local-command-[a-z]+)>.*?</\1>", "", text, flags=re.S)
    return text.strip()


def find_log(sid):
    marker = f"{TOKEN} {sid}"
    home = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    # this folder's own conversations first, however old, then the most recent from anywhere
    own = os.path.join(home, "projects", re.sub(r"[^A-Za-z0-9]", "-", ROOT))
    mine = sorted(glob.glob(os.path.join(own, "*.jsonl")), key=os.path.getmtime, reverse=True)
    rest = sorted(glob.glob(os.path.join(home, "projects", "*", "*.jsonl")), key=os.path.getmtime, reverse=True)
    for path in mine + [p for p in rest[:80] if p not in mine]:
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                if marker in f.read():
                    return path
        except OSError:
            continue
    return None


def cmd_export(args):
    sid = args[0] if args else load_current()["id"]
    path = find_log(sid)
    if not path:
        print(f"Could not find the conversation log for session {sid}. TRANSCRIPT NOT WRITTEN. Say so.")
        return False
    client = config()["name"] or "Client"
    marker = f"{TOKEN} {sid}"
    turns, started, seen = [], False, set()
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if not started and marker in line:
                started = True
                turns.append(("", "", "The clock opened here."))
                continue
            kind = d.get("type")
            queued = None
            if kind == "attachment":
                # a message sent while a reply was still being written is stored this way
                a = d.get("attachment") or {}
                if (a.get("type") == "queued_command" and (a.get("origin") or {}).get("kind") == "human"
                        and isinstance(a.get("prompt"), str)):
                    queued, kind = a, "user"
                    d = dict(d, timestamp=a.get("timestamp") or d.get("timestamp"))
            if kind not in ("user", "assistant") or d.get("isSidechain") or (d.get("isMeta") and not queued):
                continue
            if not started:
                # before the clock: keep what was said earlier the same day in this conversation
                try:
                    day = dt.datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00")).astimezone()
                except (KeyError, ValueError):
                    continue
                if f"{day:%Y-%m-%d}" != sid[:10]:
                    continue
            content = queued["prompt"] if queued else d.get("message", {}).get("content")
            texts = []
            if isinstance(content, str):
                texts = [content]
            elif isinstance(content, list):
                texts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
            body = strip_noise("\n\n".join(t for t in texts if t))
            stamp = ""
            if d.get("timestamp"):
                ts = dt.datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00")).astimezone()
                stamp = f"{ts:%H:%M}"
            # the same words from the same side in the same minute are one message logged twice
            if not body or (kind, stamp, body) in seen:
                continue
            seen.add((kind, stamp, body))
            who = client if kind == "user" else "Cate"
            turns.append((who, stamp, body))
    out = os.path.join(SESSIONS, f"{sid}-transcript.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"# Session {sid}: word-for-word transcript\n\n")
        f.write("Exported from the conversation log. Tool activity and private reasoning are left out.\n\n")
        for who, stamp, body in turns:
            if not who:
                f.write(f"*{body}*\n\n---\n\n")
                continue
            f.write(f"**{who}** ({stamp})\n\n{body}\n\n---\n\n")
    print(f"Wrote {os.path.relpath(out, ROOT)} ({len(turns)} turns).")
    return True


def cmd_backup(_args):
    dest = os.path.expanduser(config()["backup_dir"] or "")
    if not dest:
        print("No backup folder is set in .cate/config.json. Nothing copied.")
        return
    if not os.path.isdir(os.path.dirname(dest.rstrip("/\\")) or dest):
        sys.exit(f"The backup location is not available: {dest}. BACKUP NOT DONE. Say so.")
    shutil.copytree(ROOT, dest, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(".git", ".DS_Store", ".current.json"))
    if os.path.isdir(os.path.join(ROOT, ".git")):
        subprocess.run(
            ["git", "-C", ROOT, "bundle", "create", os.path.join(dest, "cate-history.bundle"), "--all"],
            check=True, capture_output=True,
        )
    print(f"Backed up to: {dest}")


def cmd_commit(message):
    if not os.path.isdir(os.path.join(ROOT, ".git")):
        return
    subprocess.run(["git", "-C", ROOT, "add", "-A"], check=True)
    changed = subprocess.run(["git", "-C", ROOT, "diff", "--cached", "--quiet"]).returncode != 0
    if changed:
        subprocess.run(["git", "-C", ROOT, "commit", "-q", "-m", message], check=True)
        print(f"Committed: {message}")


def cmd_close(_args):
    cur = load_current()
    cmd_export([cur["id"]])
    os.remove(CURRENT)
    cmd_commit(f"Session {cur['id']}")
    cmd_backup([])
    print(f"Session {cur['id']} is closed.")


if __name__ == "__main__":
    commands = {"open": cmd_open, "time": cmd_time, "tick": cmd_tick, "next": cmd_next,
                "export": cmd_export, "close": cmd_close, "backup": cmd_backup}
    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        sys.exit(__doc__)
    commands[sys.argv[1]](sys.argv[2:])
