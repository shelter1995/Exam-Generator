# 模型安装指南

## 项目所需模型清单

| 模型 | 用途 | 大小 | 是否必须 |
|------|------|------|----------|
| **BGE-M3** | 文本向量化（Embedding） | ~2.3GB | ✅ 必须 |
| **Whisper base** | 音频/视频转文字 | ~150MB | ⚠️ 音频/视频上传时需要 |
| **FFmpeg** | 视频提取音频（系统程序） | ~50MB | ⚠️ 视频上传时需要 |

---

## 你的环境现状

你的现有项目中 **已经有 BGE-M3 和 Whisper**，可以直接复用：

```
Test-System/
├── rag-core/
│   └── models/
│       ├── bge-m3/              ← ✅ 已有，约 2.3GB
│       │   ├── config.json
│       │   ├── pytorch_model.bin
│       │   ├── tokenizer.json
│       │   └── ...
│       ├── whisper/
│       │   └── base.pt          ← ✅ 已有，约 150MB
│       └── ...
└── exam-generator/              ← 新项目
    └── models/                  ← 可创建软链接或复制
```

---

## 方案一：推荐 — 直接复用已有模型（零下载）

本项目的 `config.py` 已配置为自动查找并复用 `rag-core/models/` 下的模型。

直接启动即可：

```bash
cd exam-generator
python main.py
```

如果终端显示以下内容，说明模型已正确识别：

```
[INFO] 使用本地 BGE-M3 模型: D:\GitHub_WorkSpace\Test-System\rag-core\models\bge-m3
[INFO] 使用本地 Whisper 模型: D:\GitHub_WorkSpace\Test-System\rag-core\models\whisper\base.pt
```

---

## 方案二：把模型复制到新项目目录

如果你想让新项目独立（不依赖 rag-core），复制模型文件：

### 1. 复制 BGE-M3 模型

```powershell
# PowerShell
$src = "D:\GitHub_WorkSpace\Test-System\rag-core\models\bge-m3"
$dst = "D:\GitHub_WorkSpace\Test-System\exam-generator\models\bge-m3"
New-Item -ItemType Directory -Force -Path $dst
Copy-Item -Path "$src\*" -Destination $dst -Recurse -Force
```

### 2. 复制 Whisper 模型

```powershell
$src = "D:\GitHub_WorkSpace\Test-System\rag-core\models\whisper"
$dst = "D:\GitHub_WorkSpace\Test-System\exam-generator\models\whisper"
New-Item -ItemType Directory -Force -Path $dst
Copy-Item -Path "$src\base.pt" -Destination $dst -Force
```

---

## 方案三：手动下载（如果你没有这些模型）

### 1. BGE-M3 模型下载

BGE-M3 是文本向量化的核心模型，中文效果最佳。

#### 方式 A：从 HuggingFace 下载（需要网络）

```bash
pip install huggingface-hub

# 下载到指定目录
huggingface-cli download BAAI/bge-m3 --local-dir models/bge-m3 --local-dir-use-symlinks False
```

#### 方式 B：从 ModelScope 下载（国内镜像，推荐）

```bash
pip install modelscope

python -c "
from modelscope import snapshot_download
snapshot_download('BAAI/bge-m3', cache_dir='models', local_dir='models/bge-m3')
"
```

#### 方式 C：手动下载文件

访问 https://huggingface.co/BAAI/bge-m3/tree/main 或 https://modelscope.cn/models/BAAI/bge-m3/files

下载以下关键文件到 `models/bge-m3/` 目录：

```
models/bge-m3/
├── config.json
├── config_sentence_transformers.json
├── modules.json
├── pytorch_model.bin          ← 主模型文件（约2.2GB）
├── sentence_bert_config.json
├── sentencepiece.bpe.model
├── special_tokens_map.json
├── tokenizer.json
├── tokenizer_config.json
├── 1_Pooling/
│   └── config.json
└── ... (其他辅助文件)
```

### 2. Whisper 模型下载

Whisper 用于将音频/视频中的语音转录为文字。

#### 方式 A：首次运行时自动下载

```python
import whisper
model = whisper.load_model("base")  # 自动下载到 ~/.cache/whisper/
```

下载完成后，把 `~/.cache/whisper/base.pt` 复制到 `models/whisper/base.pt`

#### 方式 B：手动下载

从 OpenAI 官方仓库下载：

```bash
# 使用 wget（需要安装）
wget -P models/whisper https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1ff5a61856120622a76ea735dc4d33d7e9f7d5b/base.pt
```

或在浏览器中访问以下链接直接下载：

```
https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1ff5a61856120622a76ea735dc4d33d7e9f7d5b/base.pt
```

保存到 `models/whisper/base.pt`

---

## FFmpeg 安装（视频处理必需）

视频上传时需要 FFmpeg 提取音频轨道，再送给 Whisper 转录。

### Windows 安装 FFmpeg

#### 方式 A：使用 Chocolatey（推荐）

```powershell
# 以管理员身份运行 PowerShell
choco install ffmpeg
```

#### 方式 B：使用 winget

```powershell
winget install Gyan.FFmpeg
```

#### 方式 C：手动下载

1. 访问 https://github.com/BtbN/FFmpeg-Builds/releases
2. 下载 `ffmpeg-master-latest-win64-gpl.zip`
3. 解压到 `C:\ffmpeg\`
4. 把 `C:\ffmpeg\bin` 添加到系统 PATH 环境变量

### 验证安装

```bash
ffmpeg -version
```

如果显示版本信息，说明安装成功。

---

## 验证所有模型就绪

在 `exam-generator` 目录下运行：

```bash
python -c "
import config
print('Embedding 模型:', config.EMBEDDING_MODEL)
print('Whisper 模型:', config.WHISPER_MODEL_PATH)
"
```

期望输出：

```
[INFO] 使用本地 BGE-M3 模型: D:\GitHub_WorkSpace\Test-System\exam-generator\models\bge-m3
[INFO] 使用本地 Whisper 模型: D:\GitHub_WorkSpace\Test-System\exam-generator\models\whisper\base.pt
Embedding 模型: D:\GitHub_WorkSpace\Test-System\exam-generator\models\bge-m3
Whisper 模型: D:\GitHub_WorkSpace\Test-System\exam-generator\models\whisper\base.pt
```

---

## 启动项目

```bash
cd exam-generator

# 配置 API Key（必须）
# 在 .env 文件中写入：
# MINIMAX_API_KEY=你的API密钥

# 启动服务
python main.py
```

然后打开浏览器访问：http://localhost:8000
