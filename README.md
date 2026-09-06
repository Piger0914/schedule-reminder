# 课表提醒（云端版）

通过 GitHub Actions 定时运行，把上课提醒、备考倒计时、王者回归提醒等推到微信（Server酱）。**云端运行，无需电脑开机，完全免费。**

## 工作原理

```
GitHub Actions 定时（每10分钟）
        ↓ 运行 reminder.py
判断当前该发什么 → 调 Server酱 → 推送到微信
        ↓
sent.json 记录已发送，防止重复推送
```

## 提醒内容一览

| 类型 | 说明 |
|------|------|
| 课程提醒 | 课前20分钟，含时间/地点/带什么 |
| 备考倒计时 | 信创赛、CMC、六级、考研，红黄绿分级（附在早课提醒里） |
| 王者回归 | 每天提醒"别登录"，10月7日可领 |
| 充电提醒 | 周日至周三 22:00 |
| 期中/期末/网课/经济学原理节点 | 一次性或每周提醒 |

## 配置步骤（首次搭建）

1. 在 GitHub 新建一个**公开**仓库（名字随意，如 `schedule-reminder`），不要初始化 README。
2. 把本项目文件推到该仓库。
3. 仓库 → **Settings → Secrets and variables → Actions → New repository secret**：
   - Name 填 `SERVERCHAN_SENDKEY`
   - Secret 填你的 Server酱 SendKey（形如 `SCT...`）
4. 到 **Actions** 标签页，点「课表提醒」→「Run workflow」手动触发一次测试。

## 为什么用公开仓库

- 公开仓库的 Actions **完全免费、不限时长**；私有仓库免费版每月仅 2000 分钟，每10分钟跑会超。
- SendKey 存放在 **Secrets** 里，代码公开也不会泄露你的推送密钥。
- 代码里只有课表信息，无敏感数据。

## 自定义

- 改课表/加倒计时：编辑 `reminder.py` 顶部的 `COURSES`、`COUNTDOWNS`、`ONE_TIME` 等数据。
- 改触发频率：编辑 `.github/workflows/reminder.yml` 里的 `cron`。

## 维护说明（重要）

**必须用真实的 `git push` 提交代码，不要用 GitHub 网页/API 直接改文件。**
用 Contents API 或网页编辑创建的提交，GitHub 的**定时调度器（schedule）不会注册**，
表现为：手动 Run workflow 能成功，但每到 cron 时间点一条都不触发。

### 网络受限时的推送方式（github.com 被墙的情况）

走 SSH over 443，可绕过大部分网络限制：

```bash
export GIT_SSH_COMMAND="ssh -o HostName=ssh.github.com -o Port=443 \
  -o StrictHostKeyChecking=accept-new -i ~/.ssh/id_ed25519"
git clone git@github.com:<用户名>/schedule-reminder.git
```

### 假期

`reminder.py` 里的 `HOLIDAYS` 列表维护法定假期，假期当天不发上课提醒，
假期前一天 20:00 会推一条假期提醒。每年国务院公布新安排后记得更新。
