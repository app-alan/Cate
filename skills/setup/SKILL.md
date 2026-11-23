---
name: setup
description: Create a new private Cate folder on this computer. Use only when the person asks to set up, install or start Cate.
---

# Create a Cate folder

Cate lives in a folder of its own on the person's computer. Your job here is only to create that folder. The setup conversation itself happens inside it, because the rules and the session clock load only when that folder is the open project.

The template is at `${CLAUDE_PLUGIN_ROOT}/skills/setup/template`. If that path does not exist, use the `template` folder beside this file.

1. Ask where the folder should go. Suggest `~/Cate`. It must be on this computer, in a place only they use. It must not be inside a git repository or a folder that syncs to other people.
2. If the folder exists and has anything in it, stop and say so. If it contains `.cate/config.json` it is already a Cate folder: tell them to open it instead. Never overwrite one.
3. Copy the template into it, including the hidden `.cate` and `.claude` folders. Rename the copied `gitignore` to `.gitignore`. Create the empty folders `sessions`, `between-sessions`, `sources`, `build` and `case/checks`.
4. In the new folder run `git init`, then block pushing so the record cannot leave by accident: write `.git/hooks/pre-push` containing a shell script that prints "This folder is private and is never pushed." and exits 1, and make it executable. Commit everything with the message "A new Cate folder".
5. Check that `python3 tools/session.py next` runs in the folder (it should say that no slots are booked). If Python 3 is missing, say so: the session clock and the transcripts need it.
6. Tell them, in a few lines:
   - where the folder is;
   - to open that folder as the project in Claude (Claude Code in a terminal, or the Code tab of the desktop app) and say "set up";
   - that the first time, Claude will ask them to trust the folder and its hook, which is the session clock in `tools/session.py`, a short script they can read;
   - that setup takes about twenty minutes without history, longer with it, and can be done in more than one sitting.

Do not begin the setup conversation here, and do not ask about their reasons for wanting it. If they say anything that suggests they may be in danger right now, that comes before everything: ask directly, give their country's emergency number, and stay with them.
