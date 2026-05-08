# SESSION.md

## 目标
在 GitHub 上创建私有仓库，推送 Exam-Generator 项目代码（排除大型二进制/模型/打包文件）。

## 当前进度
- 已分析项目结构和 .gitignore
- 正在更新 .gitignore 并创建仓库

## 关键文件
- `.gitignore` — 需要更新，把 python/、models/、ffmpeg 目录、分发包.zip 等排除
- `.env.template` — 环境变量模板（应推送）
- `.env` — 实际密钥（已排除）

## 已做改动
- 无

## 下一步
1. 更新 .gitignore，取消注释并补全大型文件排除规则
2. 用 gh CLI 创建私有仓库并推送
