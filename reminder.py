#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
课表提醒 · GitHub Actions 云端版
================================
由 GitHub Actions 定时触发（默认每 10 分钟一次），本脚本判断当前该发什么提醒，
通过 Server酱 推送到微信。云端运行，无需电脑开机，完全免费。

数据来源：石广琛 2026 秋季学期课表 + 备考计划。
"""
import os
import json
import datetime
import urllib.request
import urllib.parse
from pathlib import Path

# ---------- 基础配置 ----------
CN = datetime.timezone(datetime.timedelta(hours=8))          # 北京时间 UTC+8
SENDKEY = os.environ.get("SERVERCHAN_SENDKEY", "").strip()   # 从 GitHub Secrets 注入
STATE_FILE = Path(__file__).parent / "sent.json"             # 去重状态文件
# 补发窗口（分钟）：GitHub 定时任务可能延迟，运行迟到时仍可补发提醒
WINDOW_COURSE = 25        # 上课提醒：超过 25 分钟说明课已开始，再发没意义
WINDOW_OTHER  = 180       # 其他提醒（充电/节点/假期）：晚 3 小时内仍有意义
WEEK1_MONDAY = datetime.date(2026, 8, 31)                    # 第 1 周周一

# ---------- Server酱 推送 ----------
def send(title: str, desp: str) -> bool:
    if not SENDKEY:
        print("[skip] 未配置 SERVERCHAN_SENDKEY")
        return False
    url = f"https://sctapi.ftqq.com/{SENDKEY}.send"
    data = urllib.parse.urlencode({"title": title, "desp": desp}).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8")
            ok = '"code":0' in body.replace(" ", "") or '"code": 0' in body
            print(f"[send] {title} -> {body[:150]}")
            return ok
    except Exception as e:
        print(f"[error] 推送失败: {e}")
        return False

# ---------- 学期/周次 ----------
def teaching_week(d: datetime.date) -> int:
    return (d - WEEK1_MONDAY).days // 7 + 1

# ---------- 课程数据 ----------
# weekday: 1=周一 ... 5=周五；weeks=(起,止) 教学周
COURSES = [
    {"name": "计算机网络",        "weekday": 1, "start": "08:00", "end": "09:35", "room": "2号楼2020401",    "type": "理论课",    "bring": "平板（电子书在里面）",       "weeks": (1, 17), "important": True},
    {"name": "计算机网络实验",    "weekday": 1, "start": "09:50", "end": "11:25", "room": "学苑南楼2号楼201", "type": "实验课",    "bring": "电脑或平板（UU远程可用）",     "weeks": (1, 17), "important": True},
    {"name": "物联网控制技术",    "weekday": 1, "start": "14:30", "end": "16:05", "room": "学苑南楼1号楼204", "type": "理论+实验", "bring": "电脑或平板（UU远程可用）",     "weeks": (1, 16), "important": False},
    {"name": "无线网络技术",      "weekday": 2, "start": "08:00", "end": "09:35", "room": "2号楼2020103",    "type": "理论课",    "bring": "平板（电子书在里面）",       "weeks": (1, 17), "important": True},
    {"name": "无线网络技术实验",  "weekday": 2, "start": "09:50", "end": "11:25", "room": "1号实验楼203室",   "type": "实验课",    "bring": "电脑或平板（UU远程可用）",     "weeks": (1, 17), "important": True},
    {"name": "物联网操作系统实践","weekday": 2, "start": "14:30", "end": "16:05", "room": "1号实验楼402室",   "type": "实验课",    "bring": "电脑或平板（UU远程可用）",     "weeks": (1, 17), "important": False},
    {"name": "嵌入式系统",        "weekday": 3, "start": "08:00", "end": "09:35", "room": "2号楼2020103",    "type": "理论课",    "bring": "平板（电子书在里面）",       "weeks": (1, 17), "important": True},
    {"name": "嵌入式系统实验",    "weekday": 3, "start": "09:50", "end": "11:25", "room": "1号实验楼402室",   "type": "实验课",    "bring": "电脑或平板（UU远程可用）",     "weeks": (1, 17), "important": True},
    {"name": "计算机网络",        "weekday": 4, "start": "08:00", "end": "09:35", "room": "2号楼2020401",    "type": "理论课",    "bring": "平板（电子书在里面）",       "weeks": (1, 17), "important": True},
    {"name": "大学生职业生涯规划与就业指导(III)", "weekday": 4, "start": "09:50", "end": "11:25", "room": "3号楼2030401", "type": "理论课", "bring": "平板（电子书在里面）", "weeks": (6, 14), "important": False},
    {"name": "经济学原理",        "weekday": 4, "start": "14:30", "end": "16:05", "room": "1号楼2010506",    "type": "理论课",    "bring": "平板（电子书在里面）",       "weeks": (1, 17), "important": False},
]

# ---------- 备考倒计时 ----------
COUNTDOWNS = [
    {"name": "第三届信创赛",    "date": datetime.date(2026, 9, 24),  "note": "安徽工程大学", "emoji": "🏆"},
    {"name": "CMC数学竞赛初赛", "date": datetime.date(2026, 11, 14), "note": "",             "emoji": "🏆"},
    {"name": "大学英语六级",    "date": datetime.date(2026, 12, 12), "note": "",             "emoji": "📝"},
]
KAOYAN_NOTE = "🟢 🎓 考研（28考研·2028入学）：目标2027年12月下旬"

def countdown_block(today: datetime.date) -> str:
    lines = ["📅 备考倒计时"]
    for c in COUNTDOWNS:
        days = (c["date"] - today).days
        if days < 0:
            continue
        if days <= 7:
            dot = "🔴"
        elif days <= 30:
            dot = "🟡"
        else:
            dot = "🟢"
        note = f"（{c['note']}）" if c["note"] else ""
        lines.append(f"{dot} {c['emoji']} {c['name']}{note}：{c['date'].month}月{c['date'].day}日（还有{days}天）")
    lines.append(KAOYAN_NOTE)
    return "\n".join(lines)

# ---------- 假期（国务院 2026 放假安排，学期内部分） ----------
# 假期期间不发上课提醒；假期前一天 20:00 推一条假期提醒
HOLIDAYS = [
    (datetime.date(2026, 9, 25),  datetime.date(2026, 9, 27),  "中秋"),
    (datetime.date(2026, 10, 1),  datetime.date(2026, 10, 7),  "国庆"),
]

def holiday_of(d: datetime.date):
    """返回该日期所在的假期 (起, 止, 名称)，非假期返回 None"""
    for s, e, name in HOLIDAYS:
        if s <= d <= e:
            return (s, e, name)
    return None

# ---------- 王者回归 ----------
WZ_TARGET = datetime.date(2026, 10, 7)

def wz_block(today: datetime.date):
    if today >= WZ_TARGET:
        return None
    days = (WZ_TARGET - today).days
    return f"🎮 王者回归\n今天别登录王者！憋回归福利中，10月7日可领（还有{days}天）"

# ---------- 一次性提醒 ----------
ONE_TIME = [
    {"date": datetime.date(2026, 9, 19),  "time": "18:00", "title": "📝 经济学原理作业提醒",
     "body": "**第4周作业要交了**（本学期2次作业的第1次），记得检查是否完成再交。"},
    {"date": datetime.date(2026, 10, 25), "time": "18:00", "title": "📚 经济学原理开卷测试",
     "body": "**第9周课堂测试来了，开卷可以拿书！** 别完全不准备，熟悉下知识点位置。"},
    {"date": datetime.date(2026, 11, 15), "time": "18:00", "title": "📝 经济学原理作业提醒",
     "body": "**第12周作业要交了**（本学期最后一次作业），别漏交。"},
    {"date": datetime.date(2026, 12, 21), "time": "18:00", "title": "📚 经济学原理期末提醒",
     "body": "**第18周期末考试，闭卷！** 把两次作业和课堂测试的知识点过一遍。"},
    {"date": datetime.date(2026, 10, 19), "time": "20:00", "title": "📚 期中考试预警",
     "body": "**下周就是第9周，期中考试来了！**\n\n- 计算机网络：期中占20%，范围 Chapter 1~3\n- 嵌入式系统：平时30%+期中20%+期末50%，复习理论+作业\n- 无线网络技术：期中测验含在平时成绩里\n\n兄弟，该复习了！"},
    {"date": datetime.date(2026, 12, 14), "time": "20:00", "title": "🎙️ 期末准备提醒",
     "body": "**第16-17周，该准备期末了！**\n\n- 物联网控制技术：期末是大作业\n- 计算机网络：期末占50%，Chapter 4~6\n- 无线网络技术：期末占60%，闭卷\n\n录音准备、复习计划都该排上了。"},
    {"date": datetime.date(2026, 10, 7),  "time": "10:00", "title": "🎮 王者回归福利可领",
     "body": "**满30天啦，现在登录王者就能领回归福利！**\n\n上次登录9月6日，到今天就够30天了。登录后记得连登7天领满累登奖励（铭文特权卡、排位保护卡、英雄碎片等）。"},
]

# ---------- 周重复提醒（非课程） ----------
WEEKLY = [
    {"weekday": 6, "time": "10:00", "title": "📱 网课提醒：形势与政策",
     "body": "周末了，检查一下形势与政策的网课进度，及时完成规定任务，别拖到期末。"},
]

# ---------- 工具函数 ----------
def courses_on(day: datetime.date):
    """某天要上的课"""
    wd = day.isoweekday()
    week = teaching_week(day)
    return [c for c in COURSES if c["weekday"] == wd and c["weeks"][0] <= week <= c["weeks"][1]]

def course_title(c):
    return f"⏰{c['start']} {c['name']}·{c['room']}"

def course_body(c, today):
    periods = 2
    lines = [
        f"**⏰课程提醒：{c['name']}，即将上课，还有20分钟**",
        "",
        f"- 🕗 **{c['start']} 开始**，{c['end']} 结束（{periods}节课）",
        f"- 📍 地点：**{c['room']}**",
        f"- {c['type']}，记得带：{c['bring']}",
    ]
    if c["start"] == "08:00":
        lines.append("")
        lines.append(countdown_block(today))
        wz = wz_block(today)
        if wz:
            lines.append("")
            lines.append(wz)
    return "\n".join(lines)

def charge_body(tomorrow):
    tm = courses_on(tomorrow)
    if not tm:
        return None
    lines = ["🔋 设备充电提醒", "", f"明天（周{'一二三四五六日'[tomorrow.isoweekday()-1]}）有课："]
    for c in tm:
        lines.append(f"- {c['start']} {c['name']}（{c['room']}）")
    lines.append("")
    lines.append("理论课记得带平板（电子书在里面），实验课带电脑或平板。今晚给平板充满电！")
    return "\n".join(lines)

# ---------- 状态管理（去重） ----------
def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

def was_sent(state, day_str, eid):
    return eid in state.get(day_str, [])

def mark_sent(state, day_str, eid):
    state.setdefault(day_str, []).append(eid)

def prune_state(state, today_str):
    """只保留最近 7 天，避免文件无限增长"""
    keys = sorted(state.keys())
    keep = keys[-7:] if len(keys) > 7 else keys
    return {k: state[k] for k in keep if k <= today_str}

# ---------- 主逻辑 ----------
def main():
    # 手动触发（workflow_dispatch）时发送测试消息，用于验证链路
    if os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch":
        ok = send(
            "🎉 云端课表提醒已上线",
            "**测试消息**\n\nGitHub Actions 云端提醒已接通 Server酱！\n"
            "从现在起，不用开电脑也能收到上课提醒、备考倒计时、王者回归提醒了。\n\n"
            "今晚 22:00 会有第一条平板充电提醒，注意查收～",
        )
        print("测试消息发送:", "成功" if ok else "失败")
        return
    now = datetime.datetime.now(CN)
    today = now.date()
    today_str = today.isoformat()

    state = load_state()
    state = prune_state(state, today_str)

    # 事件列表：(触发时间, 事件ID, 标题, 正文)
    events = []

    hol_today = holiday_of(today)

    # 1) 课程提醒（提前20分钟）—— 假期期间不提醒
    if not hol_today:
        for c in courses_on(today):
            hh, mm = map(int, c["start"].split(":"))
            start_dt = datetime.datetime(today.year, today.month, today.day, hh, mm, tzinfo=CN)
            trigger = start_dt - datetime.timedelta(minutes=20)
            eid = f"course_{c['weekday']}_{c['start'].replace(':', '')}"
            events.append((trigger, eid, course_title(c), course_body(c, today), WINDOW_COURSE))

    # 2) 充电提醒（周日~周三 22:00，提醒次日）—— 次日是假期则不提醒
    if today.isoweekday() in (7, 1, 2, 3):
        tomorrow = today + datetime.timedelta(days=1)
        body = None if holiday_of(tomorrow) else charge_body(tomorrow)
        if body:
            trigger = datetime.datetime(today.year, today.month, today.day, 22, 0, tzinfo=CN)
            eid = f"charge_{today.isoweekday()}"
            events.append((trigger, eid, "🔋 平板充电提醒", body, WINDOW_OTHER))

    # 3) 周重复提醒
    for w in WEEKLY:
        if today.isoweekday() == w["weekday"]:
            hh, mm = map(int, w["time"].split(":"))
            trigger = datetime.datetime(today.year, today.month, today.day, hh, mm, tzinfo=CN)
            eid = f"weekly_{w['weekday']}_{w['time'].replace(':', '')}"
            events.append((trigger, eid, w["title"], w["body"], WINDOW_OTHER))

    # 4) 一次性提醒
    for o in ONE_TIME:
        if today == o["date"]:
            hh, mm = map(int, o["time"].split(":"))
            trigger = datetime.datetime(today.year, today.month, today.day, hh, mm, tzinfo=CN)
            eid = f"once_{o['date'].isoformat()}_{o['time'].replace(':', '')}"
            events.append((trigger, eid, o["title"], o["body"], WINDOW_OTHER))

    # 5) 假期前一天 20:00 提醒
    for s, e, name in HOLIDAYS:
        if today == s - datetime.timedelta(days=1):
            trigger = datetime.datetime(today.year, today.month, today.day, 20, 0, tzinfo=CN)
            days = (e - s).days + 1
            body = (
                f"**明天开始放 {name} 假啦（{s.month}月{s.day}日 ~ {e.month}月{e.day}日，共{days}天）**\n\n"
                f"假期期间上课提醒已自动关闭，安心休息。\n\n"
                f"顺手确认一下：假期里有没有要交的作业 / 要准备的考试？"
            )
            events.append((trigger, f"holiday_{s.isoformat()}", f"🏖️ {name}假期提醒", body, WINDOW_OTHER))

    # 发送到期且未发过的提醒
    sent_any = False
    for trigger, eid, title, body, window in events:
        if now >= trigger and not was_sent(state, today_str, eid):
            if (now - trigger).total_seconds() <= window * 60:
                ok = send(title, body)
                if ok:
                    mark_sent(state, today_str, eid)
                    sent_any = True

    if sent_any:
        save_state(state)
        print("状态已更新")
    else:
        print(f"[{now.strftime('%Y-%m-%d %H:%M')}] 当前无待发提醒")

if __name__ == "__main__":
    main()
