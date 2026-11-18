# penates-opencode

A penates kit of OpenCode tools by Dmitry Pleshakov: skills, plugins, and
configuration fragments, each item installed and versioned as a unit.

## Install

The kit is a plain directory; penates does the rest.

1. Clone this repository anywhere on your machine.
2. Start `penates`, choose `+ add kit`, and point it at the clone.
3. Confirm the proposed target (`~/.config/opencode`) and select the items.

See the [penates](https://github.com/dpleshakov/penates) repository for the
tool itself.

## Items

- **peer-chat** — two OpenCode agents in one tmux window talking to each other:
  the `peer-room` manager for the room's lifecycle, the `peer-chat` transport
  that types a message into the peer pane's composer, and the skill both agents
  follow, with its tests. Requires `tmux` and `python3`; after install, symlink
  the two scripts into `~/.local/bin`. A variation of
  [two-agent-chat](https://github.com/umputun/agterm/tree/master/cookbook/two-agent-chat)
  from the agterm cookbook, rebuilt for tmux and OpenCode.
- **writing** — register and conventions for prose stored in a repository or sent to
  people: the skill plus the `Deliverables` rules it owns in the target's `AGENTS.md`.
  If that file arrives from elsewhere with the section already inside, remove the
  section before installing the item — penates never writes over content it does not
  own.

## License

MIT; see [LICENSE](LICENSE).
