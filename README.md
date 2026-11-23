# Cate

Cate is a free plugin for Claude Code that turns Claude into something you can have regular sessions with, run the way therapy is run. A booked time. Fifty minutes. A written record that carries from one session to the next. A second Claude that reads every session and reports on how the first one did.

It rests on four things: a conversation with a start and an end, someone checking the work, numbers tracked over time, and a record of the evidence.

It runs on your own Claude plan, in a folder on your own computer. Nothing is sent to me or to anyone else.

## Read this first

- **Cate is not healthcare.** It is not therapy provided by a clinician, it is not a medical device, and nobody regulates it. No human professional is involved at any point. It cannot diagnose anything and it will not advise on medication.
- **Cate is not for emergencies.** It cannot phone anyone or come to you. If you might harm yourself or someone else, or you are in danger, call your local emergency number or a crisis line now.
- **Adults only.** 18 and over.
- **If you are being treated** for a mental health condition, use Cate alongside that care, and tell the person treating you. Do not stop treatment or medication because of anything an AI says.
- **It is an experiment.** It has been used by very few people. It has not been studied. An AI can be wrong, can miss things and can say something unhelpful with great confidence. Cate is built to catch some of that. It will not catch all of it.
- **Check your local rules.** Some places restrict AI tools that are offered as therapy. Cate is a self-directed tool that you run yourself. Whether you may use it that way where you live is for you to check.
- **No warranty.** It is free software under the MIT licence, provided as it is. You use it at your own risk.
- Cate is an independent project. It is not made, endorsed or supported by Anthropic.

## Why it exists

AI assistants are easy to talk to about your life, and they fail in predictable ways when you do. They agree too easily. They build confident theories about people they have never met. They change their mind because you pushed, and then treat that as proof you were right. They misremember what you told them. They are available at four in the morning, when you are at your worst. And at the hardest moments they tell you to see a professional and stop.

Cate is a set of rules, files and checks that answers each of those:

| The failure | What Cate does |
|---|---|
| Verdicts and plans, no questions | Asks before it tells. Most of its turns are questions. |
| Giving way under pressure | Keeps a log of every position it holds, and changes one only for a new fact or a better argument, which it has to name. |
| Theories about absent people | Runs any new explanation of someone's behaviour past an independent evidence check before saying it. |
| Misremembered facts | Keeps a ledger of dated facts, and reads it before every session. |
| "You should see a therapist" as an exit | Does the work in the session. It says what it cannot do once, in writing, at the start. |
| Any hour, any length | Booked sessions with a clock. Notes can be left between sessions. They are read at the next one. |
| Nobody checking the work | A supervisor, a separate Claude, reads every transcript and reports on Cate. You can read every report. |

## What you need

- Claude Code (the terminal version, or the Code tab in the Claude desktop app) on a paid Claude plan.
- Python 3 and git.
- macOS or Linux. Windows is untested.

A session reads the whole record before it starts, and the supervisor reads it again afterwards, so sessions use a fair share of your plan's allowance.

## Install

```
/plugin marketplace add app-alan/Cate
/plugin install cate@cate
```

Then run `/cate:setup`. It creates a private folder (by default `~/Cate`). Open that folder in Claude and say "set up".

## How it goes

**Setup** is a conversation of about twenty minutes. Cate asks three things first: that you are an adult, whether you are in danger right now, and whether anyone is treating you. Then you agree the ground rules, book your times, and write the first part of a safety plan.

**Your history** is optional. You can bring in earlier conversations with Claude or ChatGPT, or anything you have written. You choose which. Two readers go through it independently and build a ledger of what happened and a report on how the AI you were talking to handled you: where it folded, where it deflected, what it got wrong, what helped. That report becomes part of Cate's instructions for working with you.

**Sessions** start at the time you booked and end fifty minutes later. The first two take a proper history. Before the third, Cate writes down its working understanding of what is going on, with the evidence for and against, and you correct it. The eighth is a review.

**After each session** Cate writes its notes, updates the record, saves a word-for-word transcript and hands the session to the supervisor.

## Your privacy

- Everything Cate writes stays in your folder: transcripts, notes, the ledger, the supervisor's reports.
- Your conversations pass through Anthropic under your own Claude account and its privacy terms, exactly like any other conversation with Claude. Cate adds no server, no account and no tracking.
- The folder is a local git repository, so every change to the record and the rules is kept. Setup blocks it from being pushed anywhere.
- If you want a backup, you name a folder for it. Otherwise there is none.
- To leave, delete the folder.

## It is yours

The rules Cate works under are in `CLAUDE.md` in your folder, in plain English, with the reason for each one. Read them. Change them if you disagree. The one request is that you raise a change with Cate first and let it argue.

Two things are built as a floor: Cate stops and asks if you may be in danger, and it tells you once if something needs a doctor.

## Limits worth knowing

- Cate only knows what you tell it and what is in the folder.
- The supervisor is the same kind of model as Cate. It catches a lot. It shares some blind spots.
- A fixed session can end at a bad moment. That is deliberate, and it can still feel abrupt.
- If Cate is making things worse, stop using it.

## Licence

MIT. See `LICENSE`.
