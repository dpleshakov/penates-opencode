<!-- author: Dmitry Pleshakov, version: 1.4 -->
# Peer chat: operating the room

`peer-room` starts a room: a tmux session named after the project directory, holding one window with two panes, each running its own opencode TUI. `peer-chat` types a message into the other pane's composer. This file is the operator's cheat sheet; `SKILL.md` beside it is the protocol the two agents follow.

## Install

The item installs with penates into the OpenCode target; the files land in
`skills/peer-chat/`. Put the two scripts on PATH by symlinking them into
`~/.local/bin` — `peer-room` prefixes that directory onto PATH inside both
panes, so the links are enough. Requires `tmux` and `python3` besides
OpenCode itself.

<!-- Requires a penates that preserves the executable bit on file
     contributions (penates backlog: file-exec-bit); until it ships, the two
     scripts install as mode 0644 and need chmod +x before the symlinks
     work. Remove this note once that has landed. -->

## What is on screen

The terminal runs a tmux client attached to the room's session. Behind it, one tmux server keeps the window with two panes, and each pane runs a separate opencode process with its own session. Identical text in both panes is not mirroring — it is two agents doing the same task. A task belongs to exactly one pane; the other stays idle until a `Chat from …` message arrives. A new room opens with the left pane active — the natural place to give the task. Each pane carries a room name (default: left `alpha`, right `beta`); `peer-chat --check` in either pane prints both names beside the pane ids.

## Room lifecycle

- From the project directory, `peer-room` creates the room and enters it. `peer-room -n <name>` names it yourself; `peer-room --detached` creates without entering (for scripts).
- `peer-room` again, from the same directory, returns you to the existing room — it prints where that room lives before connecting, so a stale room from another project is visible before you are inside it.
- Closing the terminal window loses nothing: the tmux server keeps the room. Reopen a terminal and run `peer-room` in the project directory.
- `Ctrl+B` then `d` detaches; the room keeps running, and the terminal prints how to return and how to close.
- `Ctrl+B` then an arrow key switches panes. Mouse clicks and scrolling work too: `peer-room` turns on tmux mouse mode for the room.
- `peer-room list` shows every room: name, directory, agent names, whether someone is attached, since when.
- `peer-room close` kills the room for good, from any shell (`peer-room close -n <name>` when it is not the room of this directory). The manual equivalent is `tmux kill-session -t <name>`; killing the session kills the panes' shells.

If an agent was mid-turn when the room closed, its opencode can linger without a screen for a while. `pgrep -af opencode` shows what is left; such a process exits when its turn ends, or kill it by PID.

## Delivering a stuck message

The script removes what it typed on every failure it can observe, so a stuck draft is rare now: it appears only after an exit-2 failure (a submit that could not be confirmed, or a cleanup that could not finish). The draft shows as `Chat from <name>: …` in the peer's composer box. Press Enter in that pane to deliver it, or Ctrl+U to clear it.

A refusal before typing names its own fix: shell mode asks for Esc in the peer pane, plan mode for a switch back to build (shift+tab), a draft for patience. The messages are written for the operator; read them as given.

## Tabs

The TUI in each pane may hold several session tabs, and a delivery lands in the active tab of the receiving pane. Every `peer-chat` report names that tab; if it is not the session you expect, switch tabs in that pane yourself (`ctrl+1`…`ctrl+7` or the tab bar).

## Models

While a pane has not run its first prompt, its model display follows the machine-wide recent-models list: picking a model in one pane changes what the other pane shows. A pane stops following that list the moment you pick a model in it — the pick is held by that pane alone — and the first prompt locks it into the session. Pick each pane's model before sending the task; `peer-room` prints this reminder when it creates a room.

## Context control

One pane can reset the other's context from inside its own pane: `peer-chat compact` summarizes the peer's session in place, `peer-chat new-session` puts the peer on a fresh session (it remembers nothing afterwards — the next message must carry the full briefing). Both refuse unless the peer sits on an idle composer, and both report the peer's tab when done.

The right belongs to the panes named by `peer-room -c left|right|both` at creation (default: the left pane); it is recorded as the `@peer-control` pane option, and `peer-room list` shows the side per room. The typical shape is a lead pane on an expensive model delegating to a cheaper worker pane: a new task starts with `peer-chat new-session` plus a briefing, and `peer-chat compact` when one long task bloats the worker.

## Esc

Esc interrupts an agent only while it is working, and during a long tool call the interrupt takes effect when the call finishes. On an idle pane — for example one waiting for plan approval — there is nothing to interrupt.

## Credits

A variation of the two-agent-chat recipe from the
[agterm cookbook](https://github.com/umputun/agterm/tree/master/cookbook/two-agent-chat)
by Umputun (MIT): two agents exchanging messages typed into each other's
composer, and the delivery design — chunked typing with an on-screen marker,
per-chunk confirmation, a separately sent submit — are carried over from it,
rebuilt for tmux and OpenCode.
