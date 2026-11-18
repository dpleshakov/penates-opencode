#!/usr/bin/env python3
# author: Dmitry Pleshakov
# version: 1.3
"""Unit tests for peer-chat v3.3. Run: python3 -m unittest discover -s tests

Screen fixtures mirror real `tmux capture-pane` output from opencode 2.2.5
(calibrated 2026-11-04); the transaction tests run against a fake tmux that
models the composer's response to paste, backspace, and Enter.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import pathlib
import sys
import unittest
from importlib.machinery import SourceFileLoader
from unittest import mock

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "peer-chat"
loader = SourceFileLoader("peer_chat", str(SCRIPT))
spec = importlib.util.spec_from_loader("peer_chat", loader)
pc = importlib.util.module_from_spec(spec)
sys.modules["peer_chat"] = pc
loader.exec_module(pc)


def screen(
    draft: str = "",
    mode: str = "Build · GLM-5.3 Z.AI Coding Plan · max",
    footer: str = "shift+tab agents  ctrl+p commands",
    placeholder: str = "",
    above: list[str] | None = None,
) -> list[str]:
    """Build a composer screen in the opencode 2.2.5 layout."""
    lines = list(above or [])
    lines.append("┃")
    if draft:
        lines.append(f"┃  {draft}")
    elif placeholder:
        lines.append(f"┃  {placeholder}")
    else:
        lines.append("┃")
    lines.append("┃")
    lines.append(f"┃  {mode}")
    lines.append("╹" + "▀" * 200)
    lines.append(f" {footer}")
    return lines


class FakeTmux:
    """Models one opencode pane: composer draft, mode, busy, commands."""

    def __init__(
        self,
        draft: str = "",
        mode: str = "build",
        busy: bool = False,
        menu_commands: dict[str, str] | None = None,
    ):
        self.draft = draft
        self.mode = mode  # "build" | "shell" | "plan"
        self.busy = busy
        self.submitted: list[str] = []
        self.calls: list[tuple] = []
        self.corrupt_pastes = 0  # each drops the last 5 chars of a paste
        self.exit_after_keys: int | None = None  # pane dies after N send-keys
        self.exited = False
        self.swallow_enter = False  # Enter does not submit
        self.enter_goes_busy = True  # a submit starts the peer agent
        self.stuck_backspace = False  # BSpace has no effect
        # slash name -> menu description, offered when the draft filters it
        self.menu_commands = menu_commands if menu_commands is not None else {
            "new": "New session",
            "compact": "Compact session",
        }

    def __call__(self, *args: str) -> str:
        if not self.exited and self.exit_after_keys is not None:
            sent = sum(1 for call in self.calls if call[0] == "send-keys")
            if sent >= self.exit_after_keys:
                self.exited = True
        if self.exited and args[0] == "capture-pane":
            return "$ \n"  # opencode is gone; a bare shell remains
        if (
            self.exited
            and args[0] == "display-message"
            and "#{pane_current_command}" in args
        ):
            return "bash\n"
        self.calls.append(args)
        if args[0] == "capture-pane":
            return "\n".join(self._render())
        if args[0] == "display-message":
            if "#{pane_current_command}" in args:
                return "opencode\n"
            if "#{pane_title}" in args:
                return "OC | Fake session\n"
            return "peerlab\n"
        if args[0] == "send-keys":
            keys = (
                list(args[args.index("--") + 1 :]) if "--" in args else list(args[3:])
            )
            self._apply(keys)
            return ""
        if args[0] == "list-panes":
            return "%9|opencode\n"
        raise AssertionError(f"unexpected tmux call: {args}")

    def _apply(self, keys: list[str]) -> None:
        for key in keys:
            if key.startswith("\x1b[200~") and key.endswith("\x1b[201~"):
                text = key[len("\x1b[200~") : -len("\x1b[201~")]
                if self.corrupt_pastes > 0:
                    self.corrupt_pastes -= 1
                    text = text[:-5]
                self.draft += text
            elif key == "BSpace":
                if not self.stuck_backspace:
                    self.draft = self.draft[:-1]
            elif key == "Enter":
                if not self.swallow_enter:
                    self.submitted.append(self.draft)
                    self.draft = ""
                    self.busy = self.enter_goes_busy
            elif not key.startswith("\x1b"):
                self.draft += key  # literal -l text, as typing would
            else:
                raise AssertionError(f"unexpected key: {key!r}")

    def _menu_rows(self) -> list[str]:
        if self.busy or not self.draft.startswith("/"):
            return []
        prefix = self.draft[1:]
        return [
            f"┃ /{name}   {description}"
            for name, description in self.menu_commands.items()
            if name.startswith(prefix)
        ]

    def _render(self) -> list[str]:
        if self.busy:
            return screen(
                draft="", mode=self._mode_line(), footer="esc interrupt"
            )
        return screen(
            draft=self.draft,
            mode=self._mode_line(),
            above=self._menu_rows(),
        )

    def _mode_line(self) -> str:
        return {
            "build": "Build · GLM-5.3 Z.AI Coding Plan · max",
            "shell": "Shell",
            "plan": "Plan · GLM-5.3 Z.AI Coding Plan · max",
        }[self.mode]


class ClassifyTest(unittest.TestCase):
    def test_fresh_placeholder_is_empty(self):
        lines = screen(placeholder='Ask anything… "Fix a TODO in the codebase"')
        self.assertEqual(pc.classify(lines)[0], "empty")

    def test_session_blank_is_empty(self):
        self.assertEqual(pc.classify(screen())[0], "empty")

    def test_busy_footer_wins(self):
        lines = screen(footer="⬝⬝⬝ esc interrupt")
        state, detail = pc.classify(lines)
        self.assertEqual(state, "busy")
        self.assertIn("working", detail)

    def test_busy_words_in_old_transcript_do_not_trigger(self):
        lines = screen(above=["  the peer quoted 'esc interrupt' in an old message"])
        self.assertEqual(pc.classify(lines)[0], "empty")

    def test_shell_empty(self):
        lines = screen(
            mode="Shell",
            placeholder='Run a command… "git status"',
            footer="esc exit shell mode",
        )
        state, detail = pc.classify(lines)
        self.assertEqual(state, "shell")
        self.assertIn("shell mode", detail)

    def test_shell_with_text(self):
        lines = screen(draft="echo probe", mode="Shell", footer="esc exit shell mode")
        state, detail = pc.classify(lines)
        self.assertEqual(state, "shell")
        self.assertIn("echo probe", detail)

    def test_plan_mode(self):
        state, _ = pc.classify(screen(mode="Plan · GLM-5.3 Z.AI Coding Plan · max"))
        self.assertEqual(state, "plan")

    def test_build_draft(self):
        state, detail = pc.classify(screen(draft="hello world"))
        self.assertEqual(state, "draft")
        self.assertIn("hello world", detail)

    def test_dialog_without_rule_is_unknown(self):
        lines = [
            "  /exit                  Exit the app",
            "  /quit                  Exit the app",
            "  ┃  /ex",
        ]
        state, detail = pc.classify(lines)
        self.assertEqual(state, "unknown")
        self.assertIn("rule line", detail)


class UnitsTest(unittest.TestCase):
    def test_chunks_fit_the_char_budget(self):
        text = ("слово " * 200).strip()
        chunks = pc.text_chunks(text, 150)
        self.assertGreater(len(chunks), 1)
        self.assertEqual("".join(chunks), text)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 150)

    def test_chunks_split_huge_tokens_by_chars(self):
        chunks = pc.text_chunks("a" * 1000, 100)
        self.assertEqual("".join(chunks), "a" * 1000)
        self.assertTrue(all(len(c) <= 100 for c in chunks))

    def test_probe_marker_absent_from_text(self):
        text = "has [peer-check:0] inside"
        marker = pc.probe_marker(text)
        self.assertNotIn(marker, text)

    def test_normalize_strips_labels_and_rejects_control_chars(self):
        self.assertEqual(
            pc.normalize("Chat from alpha: hi there\nnext", "alpha"),
            "Chat from alpha: hi there next",
        )
        with self.assertRaises(pc.Refused):
            pc.normalize("bad\x1bescape", "alpha")

    def test_paste_wraps_in_bracketed_markers(self):
        sent = {}
        pc.paste("%9", "hello ! world", sh=lambda *a: sent.update(args=a))
        keys = sent["args"]
        self.assertTrue(keys[-1].startswith("\x1b[200~"))
        self.assertTrue(keys[-1].endswith("\x1b[201~"))
        self.assertIn("hello ! world", keys[-1])

    def test_tail_matches_ignores_wrap_spaces(self):
        self.assertTrue(pc.tail_matches("hello   wor ld", "hello world"))
        self.assertFalse(pc.tail_matches("hello world", "hello word"))


class ComposerWidthTest(unittest.TestCase):
    def test_width_is_the_rule_line(self):
        self.assertEqual(pc.composer_width(screen()), 200)

    def test_rule_may_carry_leading_padding(self):
        lines = screen()
        lines[-2] = "  ╹" + "▀" * 60
        self.assertEqual(pc.composer_width(lines), 60)

    def test_no_rule_line_is_none(self):
        self.assertIsNone(pc.composer_width(["$ ", ""]))


class TransactionTest(unittest.TestCase):
    def setUp(self):
        pc.CHUNK_CONFIRM_TIMEOUT = 0.3
        pc.POLL_INTERVAL = 0.01
        pc.SETTLE_BEFORE_SUBMIT = 0.0
        pc.ACCEPT_STABLE = 0.02
        pc.CLEANUP_TIMEOUT = 2.0

    def test_happy_path_multichunk_submits_clean_text(self):
        fake = FakeTmux()
        body = ("Chat from alpha: " + ("проверка доставки ! (со скобками) " * 40)).strip()
        pc.send_message("%9", body, "opencode", sh=fake)
        self.assertEqual(fake.submitted, [body])
        pastes = [c for c in fake.calls if c[0] == "send-keys" and "-l" in c]
        self.assertGreater(len(pastes), 1)  # really went in chunks
        for call in pastes:
            self.assertTrue(call[-1].startswith("\x1b[200~"))
        self.assertNotIn(" [peer-check", fake.submitted[0])
        self.assertTrue(fake.busy)

    def test_corrupted_paste_is_cleaned_up_and_refused(self):
        fake = FakeTmux()
        fake.corrupt_pastes = 1  # the first paste loses its tail (marker cut)
        body = "Chat from alpha: " + ("длинное сообщение " * 120)
        with self.assertRaises(pc.Refused) as ctx:
            pc.send_message("%9", body, "opencode", sh=fake)
        self.assertIn("composer cleaned", str(ctx.exception))
        self.assertEqual(fake.submitted, [])  # Enter never sent
        self.assertEqual(fake.draft, "")  # composer left empty

    def test_foreign_text_survives_cleanup_attempt(self):
        fake = FakeTmux()
        marker_holder = {}

        original_paste = fake._apply

        def paste_then_foreign(keys):
            original_paste(keys)
            if any(k.startswith("\x1b[200~") for k in keys):
                marker_holder["pasted"] = True
            if marker_holder.get("pasted") and fake.draft and not fake.busy:
                fake.draft += "чужой текст"  # peer started composing
                marker_holder["pasted"] = False

        fake._apply = paste_then_foreign
        with self.assertRaises(pc.Ambiguous) as ctx:
            pc.send_message("%9", "Chat from alpha: короткое сообщение", "opencode", sh=fake)
        self.assertIn("do not resend", str(ctx.exception))
        self.assertIn("чужой текст", fake.draft)  # untouched

    def test_shell_mode_is_refused_before_typing(self):
        fake = FakeTmux(mode="shell")
        with self.assertRaises(pc.Refused) as ctx:
            pc.wait_for_empty("%9", 0.5, sh=fake)
        self.assertIn("shell", str(ctx.exception))
        self.assertFalse(any(c[0] == "send-keys" for c in fake.calls))

    def test_busy_peer_is_refused_without_typing(self):
        fake = FakeTmux(busy=True)
        with self.assertRaises(pc.Refused):
            pc.wait_for_empty("%9", 0.3, sh=fake)
        self.assertFalse(any(c[0] == "send-keys" for c in fake.calls))

    def test_chip_paste_is_cleaned_blind_and_refused(self):
        fake = FakeTmux()
        original_apply = fake._apply

        def wide_paste_chips(keys):
            for key in keys:
                if key.startswith("\x1b[200~") and len(key) > 100:
                    # a paste wider than the composer collapses to a chip
                    fake.draft += "[Pasted ~1 lines]"
                    keys = []
                    break
            original_apply(keys)

        fake._apply = wide_paste_chips
        with self.assertRaises(pc.Refused) as ctx:
            pc.send_message(
                "%9", "Chat from alpha: " + ("текст " * 100), "opencode", sh=fake
            )
        self.assertIn("composer cleaned", str(ctx.exception))
        self.assertEqual(fake.submitted, [])
        self.assertEqual(fake.draft, "")

    def test_pane_command_change_aborts_mid_send(self):
        fake = FakeTmux()
        fake.exit_after_keys = 1  # opencode exits right after the first paste
        with self.assertRaises(pc.Ambiguous) as ctx:
            pc.send_message(
                "%9", "Chat from alpha: " + ("текст " * 300), "opencode", sh=fake
            )
        self.assertIn("do not resend", str(ctx.exception))
        self.assertEqual(fake.submitted, [])

    def test_accept_timeout_empty_composer_means_probable_delivery(self):
        fake = FakeTmux()
        fake.enter_goes_busy = False  # the composer empties; the peer idles
        pc.ACCEPT_STABLE = 5.0  # empty never settles within the timeout
        pc.ACCEPT_TIMEOUT = 0.3
        body = "Chat from alpha: короткое сообщение"
        with self.assertRaises(pc.Ambiguous) as ctx:
            pc.send_message("%9", body, "opencode", sh=fake)
        self.assertIn("delivery likely", str(ctx.exception))
        self.assertIn("do not resend", str(ctx.exception))
        self.assertEqual(fake.submitted, [body])  # Enter did go through
        self.assertEqual(fake.draft, "")  # nothing backspaced after it

    def test_swallowed_enter_is_cleaned_and_safe_to_retry(self):
        fake = FakeTmux()
        fake.swallow_enter = True
        pc.ACCEPT_TIMEOUT = 0.3
        with self.assertRaises(pc.Refused) as ctx:
            pc.send_message(
                "%9", "Chat from alpha: короткое сообщение", "opencode", sh=fake
            )
        self.assertIn("safe to retry", str(ctx.exception))
        self.assertEqual(fake.submitted, [])
        self.assertEqual(fake.draft, "")

    def test_busy_mid_send_leaves_the_peer_composer_untouched(self):
        fake = FakeTmux()
        original_apply = fake._apply

        def paste_then_busy(keys):
            original_apply(keys)
            if any(k.startswith("\x1b[200~") for k in keys):
                fake.busy = True  # the peer agent starts working

        fake._apply = paste_then_busy
        with self.assertRaises(pc.Ambiguous) as ctx:
            pc.send_message(
                "%9", "Chat from alpha: " + ("текст " * 100), "opencode", sh=fake
            )
        self.assertIn("do not resend", str(ctx.exception))
        self.assertEqual(fake.submitted, [])
        self.assertIn("Chat from alpha", fake.draft)  # cleanup refused to act

    def test_marker_not_removed_is_ambiguous(self):
        fake = FakeTmux()
        fake.stuck_backspace = True
        pc.CLEANUP_TIMEOUT = 0.3
        with self.assertRaises(pc.Ambiguous) as ctx:
            pc.send_message(
                "%9", "Chat from alpha: короткое сообщение", "opencode", sh=fake
            )
        self.assertIn("do not resend", str(ctx.exception))
        self.assertEqual(fake.submitted, [])


class IdentityTest(unittest.TestCase):
    def test_names_come_from_pane_options(self):
        def sh(*args):
            return {"%1": "alpha", "%9": "beta"}[args[4]] + "\n"

        with mock.patch.dict(
            os.environ, {"TMUX_PANE": "%1", "PEER_CHAT_NAME": "alpha"}
        ):
            self.assertEqual(pc.identity("%9", sh=sh), ("alpha", "beta"))

    def test_self_falls_back_to_env_peer_stays_empty(self):
        def sh(*args):
            raise RuntimeError("tmux show-options failed")

        with mock.patch.dict(
            os.environ, {"TMUX_PANE": "%1", "PEER_CHAT_NAME": "alpha"}
        ):
            self.assertEqual(pc.identity("%9", sh=sh), ("alpha", ""))

    def test_no_env_and_no_options_leave_both_empty(self):
        def sh(*args):
            return "\n"

        with mock.patch.dict(
            os.environ, {"TMUX_PANE": "%1", "PEER_CHAT_NAME": ""}
        ):
            self.assertEqual(pc.identity("%9", sh=sh), ("", ""))


class SlashControlTest(unittest.TestCase):
    def capture_sh(self, lines):
        def sh(*args):
            if args[0] == "capture-pane":
                return "\n".join(lines) + "\n"
            raise AssertionError(f"unexpected tmux call: {args}")

        return sh

    def test_menu_row_is_the_offer(self):
        lines = screen(
            draft="/new",
            above=["┃ /new                   New session"],
        )
        sh = self.capture_sh(lines)
        self.assertTrue(pc.slash_menu_visible("%9", "new", sh=sh))

    def test_bare_composer_row_is_not_the_offer(self):
        sh = self.capture_sh(screen(draft="/new"))
        self.assertFalse(pc.slash_menu_visible("%9", "new", sh=sh))

    def test_command_without_a_menu_row_is_not_offered(self):
        lines = screen(
            draft="/compact",
            above=["┃ /review   review changes"],
        )
        sh = self.capture_sh(lines)
        self.assertFalse(pc.slash_menu_visible("%9", "compact", sh=sh))

    def test_type_slash_command_sends_literal_keys(self):
        fx = FakeTmux()
        pc.type_slash_command("%9", "new", sh=fx)
        self.assertIn(("send-keys", "-t", "%9", "-l", "--", "/new"), fx.calls)
        self.assertEqual(fx.draft, "/new")
        self.assertEqual(fx.submitted, [])

    def test_type_slash_command_refuses_when_not_offered(self):
        fx = FakeTmux(menu_commands={})
        with self.assertRaises(pc.Refused) as ctx:
            pc.type_slash_command("%9", "compact", sh=fx)
        self.assertIn("does not offer", str(ctx.exception))
        self.assertEqual(fx.draft, "")

    def test_require_control_names_the_peer_pane(self):
        def sh(*args):
            if args[0] == "show-options":
                return "1\n" if args[4] == "%9" else "\n"
            raise AssertionError(f"unexpected tmux call: {args}")

        with mock.patch.dict(os.environ, {"TMUX_PANE": "%1"}):
            with self.assertRaises(pc.Refused) as ctx:
                pc.require_control("%9", sh=sh)
        self.assertIn("belong to the peer pane", str(ctx.exception))

    def test_require_control_passes_with_the_option(self):
        def sh(*args):
            if args[0] == "show-options":
                return "1\n" if args[4] == "%1" else "\n"
            raise AssertionError(f"unexpected tmux call: {args}")

        with mock.patch.dict(os.environ, {"TMUX_PANE": "%1"}):
            pc.require_control("%9", sh=sh)

    def test_wait_peer_idle_waits_through_busy(self):
        states = iter([("busy", ""), ("busy", ""), ("empty", ""), ("empty", "")])
        with mock.patch.object(
            pc, "peer_state", side_effect=lambda *a, **k: next(states)
        ), mock.patch.object(pc, "COMMAND_SETTLE_GRACE", 0.0), mock.patch.object(
            pc, "IDLE_STABLE", 0.0
        ):
            self.assertEqual(pc.wait_peer_idle("%9", 5.0), "empty")

    def test_wait_peer_idle_returns_state_at_timeout(self):
        with mock.patch.object(
            pc, "peer_state", return_value=("busy", "")
        ), mock.patch.object(pc, "COMMAND_SETTLE_GRACE", 0.0):
            self.assertEqual(pc.wait_peer_idle("%9", 0.3), "busy")


class MainTest(unittest.TestCase):
    """main() maps outcomes to exit codes and keeps the failure cause."""

    def run_main(
        self,
        argv,
        stdin_text,
        state=("empty", ""),
        send=None,
        identity=("alpha", "beta"),
        control=True,
        idle="empty",
    ):
        refuser = pc.Refused("control commands need @peer-control on this pane")
        control_patch = (
            mock.patch.object(pc, "require_control")
            if control
            else mock.patch.object(pc, "require_control", side_effect=refuser)
        )
        with mock.patch.object(
            pc, "resolve_target", return_value=("%9", "the only other pane")
        ), mock.patch.object(
            pc, "peer_state", return_value=state
        ), mock.patch.object(
            pc, "send_message", side_effect=send
        ), mock.patch.object(
            pc, "tab_suffix", return_value=""
        ), mock.patch.object(
            pc, "identity", return_value=identity
        ), control_patch, mock.patch.object(
            pc, "type_slash_command"
        ), mock.patch.object(
            pc, "submit"
        ), mock.patch.object(
            pc, "wait_peer_idle", return_value=idle
        ), mock.patch.dict(
            os.environ, {"PEER_CHAT_NAME": "alpha", "TMUX_PANE": "%1"}
        ), mock.patch(
            "sys.stdin", io.StringIO(stdin_text)
        ), mock.patch(
            "sys.argv", ["peer-chat", *argv]
        ):
            return pc.main()

    def test_exit_code_mapping(self):
        self.assertEqual(self.run_main([], "hi"), 0)
        self.assertEqual(self.run_main([], "hi", send=pc.Refused("peer busy")), 1)
        self.assertEqual(
            self.run_main([], "hi", send=pc.Ambiguous("submit unconfirmed")), 2
        )

    def test_check_reports_state_without_typing(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = self.run_main(
                ["--check"],
                "",
                state=("shell", "peer composer is in shell mode (!)"),
            )
        self.assertEqual(code, 1)
        self.assertIn("shell", out.getvalue())

    def test_check_names_both_panes(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = self.run_main(["--check"], "")
        self.assertEqual(code, 0)
        self.assertIn("self %1 alpha → %9 beta", out.getvalue())

    def test_send_report_names_panes(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = self.run_main([], "hi")
        self.assertEqual(code, 0)
        self.assertIn("sent to %9 (beta) as alpha", out.getvalue())

    def test_report_without_names_keeps_plain_form(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = self.run_main([], "hi", identity=("", ""))
        self.assertEqual(code, 0)
        self.assertIn("sent to %9 (resolved as", out.getvalue())
        self.assertNotIn("as alpha", out.getvalue())

    def test_compact_reports_compaction(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = self.run_main(["compact"], "")
        self.assertEqual(code, 0)
        self.assertIn("compacted %9 (beta) as alpha", out.getvalue())

    def test_new_session_reports_fresh_session(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = self.run_main(["new-session"], "")
        self.assertEqual(code, 0)
        self.assertIn(
            "new session for %9 (beta) as alpha — it remembers nothing",
            out.getvalue(),
        )

    def test_operation_without_control_refuses(self):
        with contextlib.redirect_stderr(io.StringIO()) as err:
            code = self.run_main(["compact"], "", control=False)
        self.assertEqual(code, 1)
        self.assertIn("@peer-control", err.getvalue())

    def test_operation_that_never_settles_is_ambiguous(self):
        with contextlib.redirect_stderr(io.StringIO()) as err:
            code = self.run_main(["compact"], "", idle="busy")
        self.assertEqual(code, 2)
        self.assertIn("inspect the peer pane", err.getvalue())

    def test_error_report_carries_the_cause(self):
        err = pc.Refused("chunk 1/2: composer cleaned; safe to retry")
        err.__cause__ = RuntimeError("peer pane now runs 'bash' mid-send")
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            code = self.run_main([], "hi", send=err)
        self.assertEqual(code, 1)
        self.assertIn("bash", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
