---
name: writing
description: How to write prose that is stored in a repository or sent to people — documentation, README and other Markdown, code comments and doc comments, commit messages, CLAUDE.md, AGENTS.md, skills, and other agent instructions. Use before writing or editing such text, however small, a one-line comment or a commit message included. Covers conventions, register, the reader, placement without duplication, durability, length, and line breaks. Not for code itself.
---

This skill applies to every text that stays in a repository or leaves the conversation.
Skills for a particular artifact, such as a changelog or a pull request description,
define the format of that artifact and apply on top of this one. The language of the
text comes from the user's and the project's instructions; this skill does not set it.

## Conventions first

Every choice of form follows the first source that settles it:

1. An explicit project rule: a formatter or linter configuration, `.editorconfig`,
   `CONTRIBUTING.md`, `CLAUDE.md`.
2. The prevailing practice of the file being edited.
3. The prevailing practice of neighbouring files of the same kind.
4. The defaults in this skill.

This covers line breaks, heading and list style, terminology, the form of comments, and
tone alike. In a file that is inconsistent, follow its prevailing practice. Text outside
the change keeps its form: restyling it is a separate change, made on request.

## Register

The register is serious and formal in any language, in documents, reports, and
specifications as much as in configuration files and agent instructions. Clarity and
precision only: no decorative analogies, no metaphors for rhythm, no digressions. A
figurative comparison that suggests itself "for clarity" is a signal to remove it. No
emoji.

## Know the reader

Decide who reads the text before writing it: who actually reads it, not what kind of
file it is.

- **An agent** — typically `CLAUDE.md`, `AGENTS.md`, skills, prompts. Write rules in
  the imperative, each with its reason when the reason is not obvious, without
  narrative. Every line costs context each time the file is loaded — `CLAUDE.md` in
  every session, a skill on every use — so leave out what the agent can learn from the
  code or from another file.
- **A person consulting a reference** — README, `CONTRIBUTING.md`, documentation. Such a
  reader arrives through a heading or a search, not by reading from the top, so headings
  name what the reader is looking for.
- **A person reading alongside a change** — code comments and commit messages. The text
  says what the code and the diff do not show: why, a constraint, a rejected
  alternative, a non-obvious consequence. It does not restate what the code says
  plainly; a short label that makes a dense expression faster to read is not a
  restatement.

A text may have two readers. A skill is run by an agent and maintained, reviewed, or
passed on by people; serve both: the rules for the agent, and the few lines a person
needs to know what the file is for and what it assumes. When the reader is unclear,
write for a person: agents read text written for people well, and people read text
written for agents poorly.

## One fact, one place

Before stating a fact, search the repository for where it is already stated. If it is
there, refer to that place instead of restating it. If the existing statement is wrong,
correct it there rather than adding a second version.

Repeat a fact only for a reason the reader benefits from — for example, keeping the
product constraints in an agent's context. Then keep the repetition short, name the
source, and update every copy in the same change as the source. A restatement in other
words is how copies drift apart.

The same applies within one text: say each thing once, in the section where a reader
would look for it.

## Write what stays true

- Leave out facts that the next release of another tool, or the next commit in this
  repository, will make false: versions, performance figures, lists of commands, files,
  or features that the code already enumerates. Where such a fact is needed, record it
  where a machine checks it — a version pin, a test, a configuration — and refer to that.
- Link outside the repository only to the authoritative source, such as a specification
  or an official reference, and only when the reader needs it.
- Avoid words that date: "currently", "now", "new", "recently", "soon".

Records whose job is to hold such facts — a changelog, a compatibility table, a dated
task file — are exempt.

## Length

- The first sentence of a section carries its point; the rest only develops it.
- Delete any paragraph whose removal costs the reader nothing.
- One example, not three.
- No sentences that announce the next one ("This section describes…") and no closing
  summary.
- No filler ("it is worth noting that") and no intensifiers ("significantly", "robust",
  "seamless"): they add length and no information.
- Parallel items are a list or a table; reasoning is prose.

## Line breaks

When the conventions above do not settle line breaks, decide by how the text is read,
not by the file type.

- **Rendered text** — Markdown that people read rendered, such as a README or
  documentation on a hosting site. Do not hard-wrap: one paragraph is one line, and the
  renderer wraps it.
- **Text read as source** — code comments, doc comments, docstrings, plain-text files,
  comments in configuration files, and Markdown read raw, such as agent instructions
  and skills. Wrap so that no line needs horizontal scrolling: within the line length
  the project's formatter or linter sets, or else within the width of the surrounding
  code or of neighbouring files. Break between phrases, not inside them.
- **Commit messages** — a short subject line, a blank line, and a body wrapped at 72
  characters, as git tooling displays it unwrapped.

When editing a paragraph in a hard-wrapped file, rewrap only that paragraph.

## Before finishing

Reread the text against these questions and revise until each answer is yes:

- Is it written for the reader it has?
- Does every paragraph add something not said above it or elsewhere in the repository?
- Will every statement hold after the next release of the tools it mentions?
- Can a reader stop after the first sentence of each section and have its point?
- Does the form match the file and the project?
