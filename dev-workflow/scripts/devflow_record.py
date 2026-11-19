"""Append rows to a change's metrics.md and validate or update the status line of its spec.md."""

import argparse
from datetime import datetime
import os
import re
import sys


PHASES = ("dev-requirements", "dev-design", "dev-build", "dev-test", "dev-release")
METRIC_PHASES = PHASES + ("合并后",)
EVENTS = (
    "阶段开始", "阶段结束", "问用户", "用户回复", "机器关口", "验证拦下问题", "返工",
    "原型实验", "用量", "合并", "上线", "合并后发现问题", "更正",
)
COUNT_EVENTS = ("验证拦下问题", "返工", "原型实验", "合并后发现问题")
TEXT_EVENTS = ("问用户", "用量", "更正")
GATE_RESULT = re.compile(r"(B|C|合并) (通过|通过，有备注|不通过)")
TIME_FORMAT = "%Y-%m-%d %H:%M"
TIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}")
METRICS_HEADER = "# 数据记录 · {name}\n\n| 时间 | 阶段 | 事件 | 值 | 说明 |\n|------|------|------|----|------|\n"
CELL_BREAK = re.compile(r"(?<!\\)\|")

STATUS_PREFIX = "状态："
STATUS_SCAN_LINES = 15
STATUS_OPTIONS = {"状态": "state", "阶段": "phase", "待关口": "gate", "等级": "level", "规模": "scale"}
STATUS_ORDER = (*STATUS_OPTIONS, "创建", "更新")
FIELD_GAP = "\u3000"
FIELD_BREAK = re.compile(r"[ \t\u3000]*[\t\u3000][ \t\u3000]*| {2,}")
DAY = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
STATES = ("草案", "已确认", "开发中", "测试中", "已验证", "已合并", "已发布", "搁置")
GATES = ("—", "评审", "A", "B", "C", "合并", "人工合并", "上生产")
ALLOWED = {
    "状态": ("|".join(STATES), "、".join(STATES)),
    "阶段": ("|".join(("—",) + PHASES), "、".join(("—",) + PHASES)),
    "待关口": ("|".join(GATES) + "|c[0-9]+|停-[0-9]+", "、".join(GATES) + "、c<数字>、停-<数字>"),
    "等级": ("L[123]( 离开)?", "L1、L2、L3，后面可以跟一个空格加“离开”"),
    "规模": ("小|标准", "小、标准"),
    "创建": (None, "YYYY-MM-DD"),
    "更新": (None, "YYYY-MM-DD"),
}


def parse_time(text, pattern, time_format):
    if pattern.fullmatch(text) is None:
        return None
    try:
        return datetime.strptime(text, time_format)
    except ValueError:
        return None


def cell(text, option):
    text = text or ""
    if "\n" in text or "\r" in text:
        raise ValueError(f"{option} 不能包含换行")
    return text.strip()


def minutes_since_last_question(table, now):
    asked = None
    for line in table.splitlines():
        cells = [part.strip() for part in CELL_BREAK.split(line.strip())[1:-1]]
        if len(cells) < 3:
            continue
        if cells[2] == "问用户":
            asked = parse_time(cells[0], TIME, TIME_FORMAT)
        elif cells[2] == "用户回复":
            asked = None
    if asked is None or now < asked:
        return ""
    return f"{int((now - asked).total_seconds() // 60)} 分钟"


def record_metric(args):
    if args.phase not in METRIC_PHASES:
        raise ValueError(f"--phase “{args.phase}”不合法，只能是：{'、'.join(METRIC_PHASES)}")
    if args.event not in EVENTS:
        raise ValueError(f"--event “{args.event}”不合法，只能是：{'、'.join(EVENTS)}")
    value = cell(args.value, "--value")
    note = cell(args.note, "--note")
    if args.event in COUNT_EVENTS and re.fullmatch("[0-9]+", value) is None:
        raise ValueError(f"事件“{args.event}”的 --value 必须是非负整数，收到“{value}”")
    if args.event == "机器关口" and GATE_RESULT.fullmatch(value) is None:
        raise ValueError(
            f"事件“机器关口”的 --value 必须是“<B|C|合并> <通过|通过，有备注|不通过>”，收到“{value}”"
        )
    if args.event in TEXT_EVENTS and not value:
        raise ValueError(f"事件“{args.event}”必须给出非空的 --value")
    if args.at is None:
        now = datetime.now().replace(second=0, microsecond=0)
    else:
        now = parse_time(args.at, TIME, TIME_FORMAT)
        if now is None:
            raise ValueError(f"--at “{args.at}”不合法，格式是 YYYY-MM-DD HH:MM")
    if not os.path.isdir(args.dir):
        raise ValueError(f"需求文件夹不存在：{args.dir}")

    path = os.path.join(args.dir, "metrics.md")
    try:
        with open(path, "rb") as file:
            existing = file.read()
    except FileNotFoundError:
        existing = b""
    if args.event == "用户回复" and args.value is None:
        value = minutes_since_last_question(existing.decode(), now)
    newline = "\r\n" if b"\r\n" in existing else "\n"
    if not existing:
        prefix = METRICS_HEADER.format(name=os.path.basename(os.path.abspath(args.dir)))
    else:
        prefix = "" if existing.endswith(b"\n") else newline
    row = "| {} | {} | {} | {} | {} |".format(
        now.strftime(TIME_FORMAT), args.phase, args.event,
        value.replace("|", "\\|"), note.replace("|", "\\|"),
    )
    with open(path, "ab") as file:
        file.write((prefix + row + newline).encode())
    return row


def parse_status(line):
    fields, extra = {}, []
    for part in FIELD_BREAK.split(line.strip()):
        key, colon, value = part.partition("：")
        if colon and key in STATUS_ORDER and key not in fields:
            fields[key] = value.strip()
        else:
            extra.append(part)
    return fields, extra


def status_problems(fields, extra):
    problems = [
        f"状态行有多余内容“{part}”（只允许 {'、'.join(STATUS_ORDER)} 各出现一次，写成“键：值”）"
        for part in extra
    ]
    problems += [f"状态行缺少字段“{key}”" for key in STATUS_OPTIONS if key not in fields]
    for key, value in fields.items():
        pattern, description = ALLOWED[key]
        if pattern is None:
            valid = parse_time(value, DAY, "%Y-%m-%d") is not None
        else:
            valid = re.fullmatch(pattern, value) is not None
        if not valid:
            problems.append(f"字段“{key}”的值“{value}”不合法，合法值：{description}")
    return problems


def update_status(args):
    today = args.today or datetime.now().strftime("%Y-%m-%d")
    if parse_time(today, DAY, "%Y-%m-%d") is None:
        raise ValueError(f"--today “{today}”不合法，格式是 YYYY-MM-DD")
    with open(args.spec, "rb") as file:
        lines = file.read().split(b"\n")
    for index, raw in enumerate(lines[:STATUS_SCAN_LINES]):
        ending = b"\r" if raw.endswith(b"\r") else b""
        line = raw[:len(raw) - len(ending)].decode()
        if line.startswith(STATUS_PREFIX):
            break
    else:
        raise ValueError(f"{args.spec} 的前 {STATUS_SCAN_LINES} 行里没有以“{STATUS_PREFIX}”开头的状态行")

    fields, extra = parse_status(line)
    changes = {
        key: getattr(args, option).strip()
        for key, option in STATUS_OPTIONS.items() if getattr(args, option) is not None
    }
    if changes:
        fields.update(changes)
        if len(changes) == len(STATUS_OPTIONS):
            extra = []
        fields.setdefault("创建", today)
        fields["更新"] = today
    problems = status_problems(fields, extra)
    if problems:
        raise ValueError("；".join(problems))
    if changes:
        line = FIELD_GAP.join(f"{key}：{fields[key]}" for key in STATUS_ORDER)
        lines[index] = line.encode() + ending
        with open(args.spec, "wb") as file:
            file.write(b"\n".join(lines))
    return line


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    metric = commands.add_parser("metric")
    metric.add_argument("--dir", required=True)
    metric.add_argument("--phase", required=True)
    metric.add_argument("--event", required=True)
    metric.add_argument("--value")
    metric.add_argument("--note")
    metric.add_argument("--at")
    status = commands.add_parser("status")
    status.add_argument("--spec", required=True)
    for option in STATUS_OPTIONS.values():
        status.add_argument(f"--{option}")
    status.add_argument("--today")
    args = parser.parse_args()

    try:
        result = record_metric(args) if args.command == "metric" else update_status(args)
    except (OSError, ValueError) as error:
        print(f"devflow record: {error}", file=sys.stderr)
        return 1

    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
