from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "dev-workflow/scripts/devflow_record.py"
HEADER = "# 数据记录 · 2026-11-02-demo\n\n| 时间 | 阶段 | 事件 | 值 | 说明 |\n|------|------|------|----|------|\n"
STATUS = "状态：开发中　阶段：dev-build　待关口：—　等级：L1　规模：标准　创建：2026-11-02　更新：2026-11-03"
SPEC = "# 演示需求\n\n{status}\n\n## 背景\n\n状态：这一行是正文，不是状态行\n"


class RecordTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.dir = Path(temp.name) / "2026-11-02-demo"
        self.dir.mkdir()
        self.metrics = self.dir / "metrics.md"
        self.spec = self.dir / "spec.md"

    def run_script(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args], text=True, capture_output=True, encoding="utf-8",
        )

    def assert_rejected(self, result, *mentions):
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertTrue(result.stderr.startswith("devflow record: "), result.stderr)
        self.assertEqual(result.stderr.count("\n"), 1, result.stderr)
        for mention in mentions:
            self.assertIn(mention, result.stderr)


class MetricTest(RecordTest):
    def metric(self, phase, event, value=None, note=None, at="2026-11-02 10:00", directory=None):
        args = ["metric", "--dir", str(directory or self.dir), "--phase", phase, "--event", event]
        for option, given in (("--value", value), ("--note", note), ("--at", at)):
            if given is not None:
                args += [option, given]
        return self.run_script(*args)

    def added(self, *args, **kwargs):
        result = self.metric(*args, **kwargs)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        row = result.stdout.rstrip("\n")
        self.assertEqual(self.metrics.read_text(encoding="utf-8").splitlines()[-1], row)
        return row

    def assert_unchanged(self, result, *mentions):
        before = self.metrics.read_bytes() if self.metrics.exists() else None
        self.assert_rejected(result, *mentions)
        self.assertEqual(self.metrics.read_bytes() if self.metrics.exists() else None, before)

    def test_creates_file_with_header_and_only_appends_afterwards(self):
        row = self.added("dev-build", "阶段开始")
        self.assertEqual(row, "| 2026-11-02 10:00 | dev-build | 阶段开始 |  |  |")
        self.assertEqual(self.metrics.read_text(encoding="utf-8"), HEADER + row + "\n")

        before = self.metrics.read_bytes()
        second = self.added("dev-build", "返工", "2", "评审打回", at="2026-11-02 11:30")
        self.assertEqual(second, "| 2026-11-02 11:30 | dev-build | 返工 | 2 | 评审打回 |")
        self.assertEqual(self.metrics.read_bytes(), before + (second + "\n").encode())

    def test_keeps_drifted_content_and_adds_missing_final_newline(self):
        drifted = HEADER + "| 昨天 | 开发 | 随手写的 | 很多 | |\n\n## 第二轮\n| 没有结尾换行 |"
        self.metrics.write_text(drifted, encoding="utf-8")
        row = self.added("合并后", "合并后发现问题", "0")
        self.assertEqual(self.metrics.read_text(encoding="utf-8"), drifted + "\n" + row + "\n")

    def test_defaults_to_current_local_time(self):
        row = self.added("dev-test", "阶段结束", at=None)
        self.assertRegex(row, r"^\| \d{4}-\d{2}-\d{2} \d{2}:\d{2} \| dev-test \| 阶段结束 \|  \|  \|$")

    def test_rejects_unknown_phase_event_and_missing_folder(self):
        self.added("dev-build", "阶段开始")
        self.assert_unchanged(self.metric("验收收口", "阶段开始"), "--phase", "验收收口", "dev-release")
        self.assert_unchanged(self.metric("dev-build", "卡住了"), "--event", "卡住了", "合并后发现问题")
        self.assert_unchanged(self.metric("dev-build", "阶段开始", at="2026/11/02 10:00"), "--at")
        self.assert_unchanged(self.metric("dev-build", "阶段开始", at="2026-11-02"), "--at")
        self.assert_unchanged(self.metric("dev-build", "阶段开始", at="2026-13-02 10:00"), "--at")

        missing = self.dir / "missing"
        self.assert_rejected(self.metric("dev-build", "阶段开始", directory=missing), "missing")
        self.assertFalse(missing.exists())

    def test_count_events_require_non_negative_integers(self):
        for event in ("验证拦下问题", "返工", "原型实验", "合并后发现问题"):
            for value in (None, "", "3（GR1–GR3）", "-1", "1.5", "三"):
                with self.subTest(event=event, value=value):
                    self.assert_unchanged(self.metric("dev-test", event, value), event, "非负整数")
            self.assertIn(f"| {event} | 3 |", self.added("dev-test", event, "3"))

    def test_machine_gate_value_has_fixed_form(self):
        for value in ("B 通过", "C 通过，有备注", "合并 不通过"):
            self.assertIn(f"| 机器关口 | {value} |", self.added("dev-test", "机器关口", value))
        for value in (None, "通过", "A 通过", "B通过", "C 通过（有备注）", "B 通过 C 通过"):
            with self.subTest(value=value):
                self.assert_unchanged(self.metric("dev-test", "机器关口", value), "机器关口")
        self.assert_unchanged(self.metric("dev-test", "机器关口", "C 通过\n"), "--value")

    def test_free_text_events_require_a_value_and_other_events_do_not(self):
        for event in ("问用户", "用量", "更正"):
            with self.subTest(event=event):
                self.assert_unchanged(self.metric("dev-design", event), event)
                self.assert_unchanged(self.metric("dev-design", event, "  "), event)
                self.assertIn(f"| {event} | 任意文本 |", self.added("dev-design", event, "任意文本"))
        for event in ("阶段开始", "阶段结束", "合并", "上线"):
            with self.subTest(event=event):
                self.assertIn(f"| {event} |  |  |", self.added("dev-release", event))

    def test_escapes_pipes_and_rejects_line_breaks(self):
        row = self.added("dev-build", "用量", "a|b", "x | y")
        self.assertEqual(row, "| 2026-11-02 10:00 | dev-build | 用量 | a\\|b | x \\| y |")
        self.assert_unchanged(self.metric("dev-build", "用量", "a\nb"), "--value")
        self.assert_unchanged(self.metric("dev-build", "用量", "a", "x\r\ny"), "--note")

    def test_user_reply_measures_minutes_since_the_open_question(self):
        self.added("dev-requirements", "问用户", "关口 A | 确认范围", at="2026-11-02 23:50")
        self.added("dev-requirements", "阶段结束", at="2026-11-02 23:55")
        row = self.added("dev-requirements", "用户回复", at="2026-11-03 00:05")
        self.assertEqual(row, "| 2026-11-03 00:05 | dev-requirements | 用户回复 | 15 分钟 |  |")

        self.added("dev-design", "问用户", "d1", at="2026-11-03 09:00")
        self.added("dev-design", "问用户", "d2", at="2026-11-04 09:00")
        row = self.added("dev-design", "用户回复", note="d2 B", at="2026-11-05 10:01")
        self.assertEqual(row, "| 2026-11-05 10:01 | dev-design | 用户回复 | 1501 分钟 | d2 B |")

    def test_user_reply_is_blank_without_an_open_question(self):
        self.assertIn("| 用户回复 |  |", self.added("dev-requirements", "用户回复"))
        self.added("dev-requirements", "问用户", "关口 A", at="2026-11-02 10:00")
        self.assertIn("| 用户回复 | 5 分钟 |", self.added("dev-requirements", "用户回复", at="2026-11-02 10:05"))
        self.assertIn("| 用户回复 |  |", self.added("dev-requirements", "用户回复", at="2026-11-02 10:30"))

    def test_user_reply_keeps_an_explicit_value(self):
        self.added("dev-requirements", "问用户", "关口 A", at="2026-11-02 10:00")
        row = self.added("dev-requirements", "用户回复", "约 2 小时", at="2026-11-02 10:05")
        self.assertIn("| 用户回复 | 约 2 小时 |", row)


class StatusTest(RecordTest):
    def write_spec(self, status=STATUS, newline="\n"):
        content = SPEC.format(status=status).replace("\n", newline).encode()
        self.spec.write_bytes(content)
        return content

    def status(self, *args):
        return self.run_script("status", "--spec", str(self.spec), *args)

    def assert_unchanged(self, before, result, *mentions):
        self.assert_rejected(result, *mentions)
        self.assertEqual(self.spec.read_bytes(), before)

    def test_check_mode_prints_valid_line_without_writing(self):
        for status in (
            STATUS,
            "状态：草案  阶段：—\t待关口：评审　 等级：L3 离开　规模：小",
            "状态：已发布　规模：标准　阶段：dev-release　待关口：上生产　等级：L2",
        ):
            with self.subTest(status=status):
                before = self.write_spec(status)
                result = self.status()
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, status + "\n")
                self.assertEqual(self.spec.read_bytes(), before)

    def test_check_mode_names_the_broken_field(self):
        cases = (
            ("状态：开发中", "状态：已验证，可审查工作树", ("“状态”", "已验证，可审查工作树", "已合并")),
            ("阶段：dev-build", "阶段：验收收口", ("“阶段”", "验收收口", "dev-release")),
            ("等级：L1", "等级：L1，本次机器关口自动推进", ("“等级”", "L1，本次机器关口自动推进", "L3")),
            ("等级：L1", "等级：L1  离开", ("离开",)),
            ("规模：标准", "规模：大", ("“规模”", "大", "标准")),
            ("创建：2026-11-02", "创建：2026/11/02", ("“创建”", "YYYY-MM-DD")),
            ("更新：2026-11-03", "更新：2026-02-30", ("“更新”", "YYYY-MM-DD")),
            ("待关口：—　", "", ("缺少", "“待关口”")),
            ("　规模：标准", "", ("缺少", "“规模”")),
            ("　规模：标准", "　规模：标准　负责人：某人", ("负责人：某人",)),
            ("　规模：标准", "　规模：标准　阶段：dev-test", ("阶段：dev-test",)),
            ("阶段：dev-build", "阶段:dev-build", ("阶段:dev-build", "缺少", "“阶段”")),
        )
        for old, new, mentions in cases:
            with self.subTest(new=new):
                before = self.write_spec(STATUS.replace(old, new))
                self.assert_unchanged(before, self.status(), *mentions)

    def test_requires_an_existing_status_line_near_the_top(self):
        self.spec.write_bytes(b"# title\n\nno status here\n")
        self.assert_unchanged(b"# title\n\nno status here\n", self.status("--state", "草案"), "状态行")

        late = ("# title\n" + "\n" * 14 + STATUS + "\n").encode()
        self.spec.write_bytes(late)
        self.assert_unchanged(late, self.status(), "状态行")

        self.spec.unlink()
        self.assert_rejected(self.status(), "spec.md")

    def test_update_rewrites_only_the_status_line(self):
        before = self.write_spec("状态：开发中\t阶段：dev-build  待关口：—　等级：L1　规模：标准　更新：2026-11-03　创建：2026-11-02")
        result = self.status("--state", "测试中", "--phase", "dev-test", "--today", "2026-11-09")
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = "状态：测试中　阶段：dev-test　待关口：—　等级：L1　规模：标准　创建：2026-11-02　更新：2026-11-09"
        self.assertEqual(result.stdout, expected + "\n")
        lines = before.decode().split("\n")
        lines[2] = expected
        self.assertEqual(self.spec.read_bytes(), "\n".join(lines).encode())

    def test_update_fills_missing_created_date_and_defaults_to_today(self):
        self.write_spec("状态：草案　阶段：dev-requirements　待关口：A　等级：L2　规模：小")
        result = self.status("--level", "L2 离开", "--today", "2026-11-09")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "状态：草案　阶段：dev-requirements　待关口：A　等级：L2 离开　规模：小　创建：2026-11-09　更新：2026-11-09\n",
        )
        result = self.status("--gate", "—")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(result.stdout, r"　待关口：—　等级：L2 离开　规模：小　创建：2026-11-09　更新：\d{4}-\d{2}-\d{2}\n$")

    def test_update_rejects_invalid_results_without_writing(self):
        before = self.write_spec()
        self.assert_unchanged(before, self.status("--state", "已验证，可审查工作树"), "“状态”")
        self.assert_unchanged(before, self.status("--phase", "验收收口"), "“阶段”")
        self.assert_unchanged(before, self.status("--level", "L4"), "“等级”")
        self.assert_unchanged(before, self.status("--scale", ""), "“规模”")
        self.assert_unchanged(before, self.status("--state", "测试中", "--today", "11-09"), "--today")

        before = self.write_spec(STATUS.replace("阶段：dev-build", "阶段：验收收口"))
        self.assert_unchanged(before, self.status("--state", "测试中"), "“阶段”", "验收收口")

    def test_one_full_update_repairs_a_broken_line(self):
        broken = "状态：已验证，可审查工作树　阶段：验收收口　等级：L1，本次机器关口自动推进　规模：中等　创建：2026-11-02　更新：昨天　备注：等用户"
        before = self.write_spec(broken)
        self.assert_unchanged(before, self.status("--state", "已验证", "--phase", "dev-test"), "“待关口”")
        result = self.status(
            "--state", "已验证", "--phase", "dev-test", "--gate", "合并", "--level", "L1",
            "--scale", "标准", "--today", "2026-11-09",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = "状态：已验证　阶段：dev-test　待关口：合并　等级：L1　规模：标准　创建：2026-11-02　更新：2026-11-09"
        self.assertEqual(result.stdout, expected + "\n")
        self.assertEqual(self.spec.read_bytes(), before.replace(broken.encode(), expected.encode()))
        self.assertEqual(self.status().stdout, expected + "\n")

    def test_gate_values(self):
        for gate in ("—", "评审", "A", "B", "C", "合并", "人工合并", "上生产", "c3", "c12", "停-1", "停-2"):
            with self.subTest(gate=gate):
                self.write_spec()
                result = self.status("--gate", gate, "--today", "2026-11-09")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"　待关口：{gate}　", result.stdout)
        for gate in ("c", "D", "C3", "c-1", "停", "停-", "停-x", "A 通过", "无"):
            with self.subTest(gate=gate):
                before = self.write_spec()
                self.assert_unchanged(before, self.status("--gate", gate), "“待关口”", "c<数字>")

    def test_crlf_file_stays_crlf(self):
        before = self.write_spec(newline="\r\n")
        result = self.status("--gate", "C", "--today", "2026-11-09")
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = "状态：开发中　阶段：dev-build　待关口：C　等级：L1　规模：标准　创建：2026-11-02　更新：2026-11-09"
        self.assertEqual(result.stdout, expected + "\n")
        after = self.spec.read_bytes()
        self.assertEqual(after, before.replace(STATUS.encode(), expected.encode()))
        self.assertEqual(after.count(b"\r\n"), after.count(b"\n"))


if __name__ == "__main__":
    unittest.main()
