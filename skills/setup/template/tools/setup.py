#!/usr/bin/env python3
"""The setup checklist for a Cate folder.

Setup is a fixed list of steps. This script holds the list, knows which step
is next, and will not let the list be skipped or left half done.

  setup.py begin             start setup: note which folder is being set up,
                             then print the first step
  setup.py next              print the step to ask now
  setup.py done ID           mark a step answered, commit, print the next one
  setup.py halt REASON       stop setup (under 18, or they say they are in danger now)
  setup.py resume            carry on after a halt
  setup.py remind            one reminder, silent once setup is complete
                             (the prompt hook runs this)
  setup.py guard             refuse a reply that ends without the next
                             question (the stop hook runs this)

With --plugin, remind and guard are being run by the Cate plugin's own hooks,
for a setup conversation that is happening in a chat outside this folder. They
find the folder from a one-line note, ~/.cate-setup-folder, which "begin"
writes and the last step removes.

Nothing here sends anything anywhere.
"""
import datetime as dt
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, ".cate", "config.json")
POINTER = os.path.join(os.path.expanduser("~"), ".cate-setup-folder")

PARTS = {
    1: "What this is",
    2: "How Cate works with you",
    3: "When you meet",
    4: "Anything Cate should read first",
    5: "Reading it back",
}

# Each step: id, part, a short title, and the brief for Claude.
STEPS = [
    ("age", 1, "Age", """
This is the very first message of setup. Before the question, tell them in a few plain sentences:
- what this is: Cate runs regular sessions at fixed times, with a written record, and does the job a therapist does. Claude is not a licensed clinician, nobody regulates this, it is not healthcare and it is not an emergency service: it cannot phone anyone or come to them.
- where things go: everything they tell it is kept in this folder on their own computer. The conversation itself passes through Anthropic under their own Claude account, like any other chat. Nothing is sent to the person who made Cate.
- what happens now: about fifteen minutes of short questions, one at a time, in five parts. You will lead and they only have to answer. If they have to stop, they can come back and it picks up where it left off.
Then ask: "First, are you 18 or over?"
If the answer is no: say this was built for adults, suggest they talk to an adult they trust, run `python3 tools/setup.py halt under-18` (in this folder), and stop.
Write the answer at the top of `case/agreement.md`."""),
    ("treatment", 1, "Current care", """
Say why you ask: Cate should work alongside any care they already have, and it never advises on medicines.
Ask: "Is anyone treating you at the moment, such as a doctor, a psychiatrist or a therapist, and do you take any medication for your mood, your sleep or your mind?"
If yes, say once that Cate runs alongside that care and does not replace it. If they describe something that needs a doctor's assessment (see "Something talking cannot do" in `CLAUDE.md`), say so once, plainly.
Write the answer at the top of `case/agreement.md` and in `case/history.md`."""),
    ("name", 1, "Their name", """
Ask: "What should Cate call you?"
Write the name and today's date at the top of `case/agreement.md`, and set `name` in `.cate/config.json`."""),
    ("referrals", 2, "Doing the work here", """
Introduce the part: the next few questions are about how Cate works. Each one has a usual answer. They can keep it or change it, and what they decide is written into an agreement they can read and change later.
Explain this one: most AI assistants, when a subject gets hard, say "you should talk to a therapist" and stop. Cate does not do that. It stays and does the work with them. There are two exceptions: if they tell it they are in danger right now, it stops and asks, and if something needs a doctor, it says so once.
Ask: "Is that what you want?"
If they would sooner have Cate suggest outside help more freely, write that into the agreement in their words."""),
    ("length", 2, "Session length", """
Explain: a session is 50 minutes and Cate ends it on time, even mid-thought, the way a consulting room does. A fixed end is part of what makes it work.
Ask: "Does 50 minutes suit you, or would you like a different length?"
If different, set `session_minutes` in the config (and `warn_minutes` to five less) and change the agreement."""),
    ("moving", 2, "Moving a start", """
Explain: sometimes a person wants to start a little early or late on the day. It is easier to decide the rule now than to argue it at the door.
Ask: "On the day, should you be able to move the start by up to fifteen minutes if you ask beforehand, or should the booked time be fixed?"
Write their choice into the agreement and delete the other option."""),
    ("between", 2, "Between sessions", """
Explain: there are no sessions between sessions. They can leave a note for Cate at any hour, in a folder called `between-sessions`, and it is read at the start of the next session, not answered before. This is deliberate: it keeps the work inside the hour.
Ask: "Is that all right with you?"
Write any change into the agreement."""),
    ("badhours", 2, "A rule for bad hours", """
Explain: some people have hours when they decide badly, often late at night, and find it helps to have a rule of their own for those hours. An example: nothing is sent and nothing is decided at night.
Ask: "Are there hours like that for you, and do you want a rule for them?"
Write the rule into the agreement in their words, or "none"."""),
    ("working", 2, "Three more things", """
Tell them three things, briefly, in plain words:
- after every session a second, separate Claude reads the whole session and writes a report on how well Cate did its job. The report is about Cate, not about them, and they can read every one.
- Cate holds a view until a new fact or a better argument changes it. It will not just give way because they push, and it will say so when it thinks that is happening.
- the rules Cate works under are theirs and they can change them. The way to do it is to raise it with Cate first.
Ask: "Do you want any of those three changed?"
Write any change into the agreement."""),
    ("fence", 2, "Anything off limits", """
Ask: "Is there any subject you do not want Cate to raise? You only need to name it. You do not have to say anything about it."
Write it into the agreement as a fence, with no detail, or "none"."""),
    ("when", 3, "Days and time", """
Introduce the part: now the times. Sessions happen at a fixed time each week, like an appointment.
Suggest the usual pattern: twice a week for the first eight sessions, then weekly, at a time of day when they are usually at their clearest and never their worst hours.
Ask: "Which days and what time would suit you?"
If the answer leaves out how often, the days or the time, ask for the missing piece before you mark this step done. Take the time zone from this computer and say which one you are using.
Write the slots into the agreement with the dates of the first eight sessions, and into `slots` in the config, like {"day": "Mon", "time": "10:00"}."""),
    ("auto", 3, "Starting a session", """
Explain how a session starts: they open this folder in Claude at the booked time and say they are here for their session. If this app can schedule tasks, it can also open the session by itself so that Cate is ready and waiting.
If a tool for scheduled tasks is available in this app, ask: "Would you like the session to open by itself at the booked time?" If yes, create one recurring task for each slot, in this folder, set to start FIVE MINUTES BEFORE the booked time so that Cate has done its reading and is ready on the hour. The task's prompt is: "This is a scheduled Cate session. Booked time HH:MM. You have been started five minutes early so that you are ready at the booked time." Record in the agreement that sessions open by themselves.
If no such tool is available, do not offer it. Tell them how to start a session, and ask: "Is that clear?"
Either way, say that the clock runs from the booked time whether they are there or not."""),
    ("extra", 3, "Extra sessions", """
Explain: if something cannot wait for the next session, they can ask for an extra one. It is a full session with a start and an end, booked for the same day or the next, and never in their bad hours.
Ask: "Between which hours of the day should an extra session be allowed?"
Write the hours into the agreement."""),
    ("backup", 3, "A backup", """
Explain: this folder is the only copy of their record. It can copy itself to another folder on this computer at the end of each session, for example a folder inside a cloud drive they already use. It must never be put on GitHub or anywhere other people can reach, and the setup has blocked that.
Ask: "Do you want a backup copy kept, and if so, in which folder?"
Put the path in `backup_dir` in the config, or leave it empty, and write the choice into the agreement."""),
    ("reading", 4, "Earlier conversations or writing", """
This step needs explaining, because nothing about it is obvious. Say something close to this, in your own words:
"There is one optional step left. If you have already talked about what is on your mind with an AI such as Claude or ChatGPT, or written about it in a journal, notes or letters, Cate can read that first. Then your first session starts from what you have already said and you do not have to tell it all again. Cate also looks at where those earlier conversations let you down, so that it does not repeat them. You choose exactly what it reads, and it stays in this folder on your computer. Reading takes from ten minutes to an hour or more, depending on how much there is. If you have nothing like that, or would sooner start fresh, the first session simply begins by asking about you, and you can add material at any later point."
Ask: "Do you have anything like that you would like Cate to read first?"
If no: mark this step done.
If yes: follow "Reading what they bring" in `SETUP.md`, one source at a time, and mark this step done only when the starting record is written."""),
    ("readback", 5, "The agreement, read back", """
Say this is the last step. Read `case/agreement.md` back to them in plain words, keeping it short: what they chose, and anything that differs from the usual. Every blank in the file must be filled in before you ask.
Ask: "Is all of that right, or is there anything to change?"
Change what they ask, and ask again until they say it is right. Then change the Status line of the agreement to say it was agreed at setup on today's date, and mark this step done."""),
]

IDS = [s[0] for s in STEPS]

FINISH = """SETUP IS COMPLETE. This is the one message in setup that does not end with a question.
Tell them, briefly and plainly:
- setup is finished, and when their first session is (run `python3 "{root}/tools/session.py" next`).
- how a session starts: this folder open as the project in Claude (Claude Code in a terminal, or the Code tab of the desktop app), at the booked time, and they say they are here for their session. If you scheduled it to open by itself, say that Cate will be there waiting.
- the folder's path: {root}
- the first time they open the folder, Claude will ask them to trust it and its hooks. The hooks are the session clock and this checklist, two short scripts in `tools/` that they can read.
- everything in the folder is theirs to read, including `CLAUDE.md`, the rules Cate works under.
Then stop. Do not begin the session, and do not ask how they are feeling about it."""


def load():
    with open(CONFIG, encoding="utf-8") as f:
        return json.load(f)


def save(cfg):
    with open(CONFIG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")


def pending(cfg):
    done = set(cfg.get("setup_done", []))
    for step in STEPS:
        if step[0] not in done:
            return step
    return None


def active(cfg):
    """True while setup is unfinished and not halted."""
    return not cfg.get("setup_complete") and not cfg.get("setup_halted")


def headline(cfg, step):
    n = IDS.index(step[0]) + 1
    return (f"SETUP IS NOT FINISHED. Next: step {n} of {len(STEPS)} "
            f"(part {step[1]} of {len(PARTS)}, \"{PARTS[step[1]]}\"): {step[2]}.")


def show(cfg):
    if cfg.get("setup_halted"):
        print(f"Setup is halted ({cfg['setup_halted']}). To carry on: python3 \"{ROOT}/tools/setup.py\" resume")
        return
    step = pending(cfg)
    if cfg.get("setup_complete") or step is None:
        print("Setup is complete.")
        return
    print(headline(cfg, step))
    print(step[3].strip())
    print()
    print(f"Every file named above is inside {ROOT}")
    print(f"When they have answered and you have written it down, run: python3 \"{ROOT}/tools/setup.py\" done {step[0]}")
    print("That prints the next step. Ask it in the SAME message. A setup message that ends without a "
          "question is a stall, and the person is left not knowing what to do.")


def commit(message):
    if not os.path.isdir(os.path.join(ROOT, ".git")):
        return
    subprocess.run(["git", "-C", ROOT, "add", "-A"], check=False)
    if subprocess.run(["git", "-C", ROOT, "diff", "--cached", "--quiet"]).returncode != 0:
        subprocess.run(["git", "-C", ROOT, "commit", "-q", "-m", message], check=False)


def cmd_next(_args):
    show(load())


def cmd_begin(_args):
    with open(POINTER, "w", encoding="utf-8") as f:
        f.write(ROOT + "\n")
    show(load())


def clear_pointer():
    try:
        with open(POINTER, encoding="utf-8") as f:
            if f.read().strip() == ROOT:
                os.remove(POINTER)
    except OSError:
        pass


def plugin_mode(event):
    """Point at the folder being set up, if this chat is the one setting it up.

    Returns False when the plugin's hooks have nothing to do: no setup under
    way, the chat is already inside the folder (its own hooks cover it), or
    this chat has never touched that folder's checklist.
    """
    global ROOT, CONFIG
    try:
        with open(POINTER, encoding="utf-8") as f:
            folder = f.read().strip()
    except OSError:
        return False
    if not folder or not os.path.exists(os.path.join(folder, ".cate", "config.json")):
        return False
    cwd = os.path.realpath(event.get("cwd") or os.getcwd())
    real = os.path.realpath(folder)
    if cwd == real or cwd.startswith(real + os.sep):
        return False
    path = event.get("transcript_path")
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            log = f.read()
    except (OSError, TypeError):
        return False
    if "tools/setup.py" not in log or os.path.basename(real) not in log:
        return False
    ROOT, CONFIG = folder, os.path.join(folder, ".cate", "config.json")
    return True


def read_event():
    try:
        return json.load(sys.stdin)
    except ValueError:
        return {}


def cmd_done(args):
    cfg = load()
    step = pending(cfg)
    if step is None or cfg.get("setup_complete"):
        sys.exit("Setup is already complete.")
    if not args or args[0] != step[0]:
        sys.exit(f"The step to finish now is \"{step[0]}\" ({step[2]}). Steps are done in order, "
                 f"and none is skipped. Run: python3 tools/setup.py next")
    cfg.setdefault("setup_done", []).append(step[0])
    nxt = pending(cfg)
    if nxt is None:
        cfg["setup_complete"] = True
        cfg["setup_stage"] = "done"
        save(cfg)
        clear_pointer()
        commit("Setup complete")
        print(FINISH.format(root=ROOT))
        return
    cfg["setup_stage"] = str(nxt[1])
    save(cfg)
    commit(f"Setup: {step[2]}")
    if nxt[1] != step[1]:
        print(f"Part {step[1]} of {len(PARTS)} is done. Say so in one line, then go on.")
    show(cfg)


def cmd_halt(args):
    cfg = load()
    cfg["setup_halted"] = " ".join(args) or "halted"
    save(cfg)
    commit(f"Setup halted: {cfg['setup_halted']}")
    print("Setup is halted. Nothing more is asked until: python3 tools/setup.py resume")


def cmd_resume(_args):
    cfg = load()
    cfg.pop("setup_halted", None)
    save(cfg)
    show(cfg)


def cmd_remind(args):
    if "--plugin" in args and not plugin_mode(read_event()):
        return
    try:
        cfg = load()
    except (OSError, ValueError):
        return
    step = pending(cfg)
    if not active(cfg) or step is None:
        return
    print(headline(cfg, step))
    print("You are setting this folder up with a person who has never done it before. Your one aim in "
          "this chat is to reach \"Setup complete\". Whatever they have just said, deal with it, then run "
          f"`python3 \"{ROOT}/tools/setup.py\" next` and end your reply with that step's question.")


def last_reply(event):
    text = event.get("last_assistant_message")
    if isinstance(text, str) and text.strip():
        return text
    path = event.get("transcript_path")
    if not path or not os.path.exists(path):
        return None
    found = None
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("type") != "assistant" or d.get("isSidechain"):
                continue
            content = d.get("message", {}).get("content")
            if isinstance(content, str):
                parts = [content]
            else:
                parts = [b.get("text", "") for b in content or [] if isinstance(b, dict) and b.get("type") == "text"]
            joined = "\n".join(p for p in parts if p.strip())
            if joined:
                found = joined
    return found


def cmd_guard(args):
    """Stop hook. Blocks, once, a reply that ends setup's turn without a question."""
    event = read_event()
    if event.get("stop_hook_active"):
        return
    if "--plugin" in args and not plugin_mode(event):
        return
    try:
        cfg = load()
    except (OSError, ValueError):
        return
    step = pending(cfg)
    if not active(cfg) or step is None:
        return
    text = last_reply(event)
    if text is None or "?" in text.strip()[-400:]:
        return
    reason = (
        f"{headline(cfg, step)} Your reply ended without a question, so the person has been left with "
        f"nothing to answer. Do not apologise or explain. Run `python3 \"{ROOT}/tools/setup.py\" next` and ask that "
        "step's question now, in full. The only reasons to end a setup reply without a question are that "
        "the person has said they need to stop (then tell them exactly how to come back: open this folder "
        "in Claude and say \"carry on with setup\"), or that you are waiting for reader agents to finish "
        "(then say so, and say that you will carry on by yourself when they do)."
    )
    print(json.dumps({"decision": "block", "reason": reason}))


if __name__ == "__main__":
    commands = {"begin": cmd_begin, "next": cmd_next, "done": cmd_done, "halt": cmd_halt, "resume": cmd_resume,
                "remind": cmd_remind, "guard": cmd_guard}
    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        sys.exit(__doc__)
    commands[sys.argv[1]](sys.argv[2:])
