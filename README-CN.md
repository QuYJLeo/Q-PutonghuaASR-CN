# Q-PutonghuaASR-CN

高性能普通话自动语音识别（ASR）系统，支持实时流式识别和离线批处理功能。

## 目录

- [功能特性](#功能特性)
- [系统架构](#系统架构)
- [快速开始](#快速开始)
- [安装步骤](#安装步骤)
- [使用方法](#使用方法)
- [API 文档](#api-文档)
- [配置说明](#配置说明)
- [项目结构](#项目结构)
- [许可证](#许可证)

## 功能特性

- **实时流式ASR**: 低延迟实时语音识别
- **离线批处理**: 高精度离线语音识别
- **混合模式**: 流式转离线处理，提升识别准确率
- **语音活动检测（VAD）**: 自动语音分段
- **标点恢复**: 自动标点插入
- **热词支持**: 可自定义热词增强
- **多进程架构**: 支持并发处理
- **WebSocket通信**: 实时双向通信
- **跨平台支持**: 支持Windows和Linux系统

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        客户端层                                │
│  [Socket.IO客户端]  [HTTP客户端]  [WebSocket客户端]            │
└───────────────────────────┬───────────────────────────────────┘
                            │
┌───────────────────────────▼───────────────────────────────────┐
│                       服务端层                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐   │
│  │ SocketIOServer│  │  SessionServer│  │    AuthManager   │   │
│  └──────┬───────┘  └──────┬───────┘  └───────────────────┘   │
│         │                 │                                   │
│         ▼                 ▼                                   │
│  ┌──────────────┐  ┌──────────────┐                           │
│  │   AsrServer  │  │   WorkerPool │                           │
│  └──────┬───────┘  └──────┬───────┘                           │
│         │                 │                                   │
│         ▼                 ▼                                   │
│  ┌─────────────────────────────────────────┐                 │
│  │            ASR多进程Worker              │                 │
│  │  ┌─────────┐ ┌─────────┐ ┌───────────┐ │                 │
│  │  │ ASRFlow │ │AsrOneFlow││Streaming2 │ │                 │
│  │  │(在线模式)│ │(离线模式)││Offline    │ │                 │
│  │  └─────────┘ └─────────┘ └───────────┘ │                 │
│  └─────────────────────────────────────────┘                 │
└───────────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼───────────────────────────────────┐
│                      模型层                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────┐  │
│  │ SeacoParaformer │  │   FSMN-VAD      │  │CT-Transformer │  │
│  │    (语音识别)    │  │  (语音活动检测) │  │   (标点恢复)   │  │
│  └─────────────────┘  └─────────────────┘  └───────────────┘  │
└───────────────────────────────────────────────────────────────┘
```

## 快速开始

### 环境要求

- Python 3.8+
- PyTorch 1.8+
- CUDA 10.2+（用于GPU加速）

### 安装步骤

```bash
# 克隆仓库
git clone https://github.com/your-repo/Q-PutonghuaASR-CN.git
cd Q-PutonghuaASR-CN

# 安装依赖
pip install -r requirements.txt

# 下载预训练模型（放置在 weights/ 目录）
# 详见模型要求部分
```

### 启动服务

```bash
# 启动ASR服务
python main.py
```

## 安装步骤

### 环境设置

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 安装所需包
pip install torch torchvision torchaudio
pip install funasr funasr_onnx
pip install eventlet python-socketio
pip install flask flask-basicauth
pip install psutil pyaudio
pip install librosa noisereduce
pip install cryptography pyDes
```

### 模型要求

下载以下预训练模型并放置在 `weights/` 目录：

1. **SeacoParaformer (离线ASR)**: `speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch`
2. **Paraformer Online**: `speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online`
3. **FSMN-VAD**: `speech_fsmn_vad_zh-cn-16k-common-pytorch`
4. **CT-Transformer (标点恢复)**: `punc_ct-transformer_zh-cn-common-vocab272727-pytorch`

## 使用方法

### 启动服务端

```python
from server.asr_server import AsrServer
from utils.Logger import loadLoggingConfig

# 加载日志配置
loadLoggingConfig()

# 创建并启动服务
asr_server = AsrServer(
    host='0.0.0.0',
    port=6060,
    cors_origins='*'
)
asr_server.start()
asr_server.join()
```

### 客户端示例

```python
from client.socket_io_client import SocketIOClient

# 创建客户端
client = SocketIOClient('http://localhost:6060')

# 设置事件监听器
def on_message(data):
    print(f"收到消息: {data}")

client.setMessageListener(on_message)
client.connect()

# 发送音频数据
client.sendVoice(times=0, voice=audio_bytes)

# 发送命令
client.sendCommand({"command": "START", "config": {"offline": False}})
```

## API 文档

### Socket.IO 事件

#### 客户端到服务端

| 事件 | 描述 | 参数 |
|-------|-------------|------------|
| `command` | 发送控制命令 | `{"command": "START\|STOP\|END", "config": {...}}` |
| `voice` | 发送音频数据 | `{"times": 时间戳, "voice": 字节数据}` |

#### 服务端到客户端

| 事件 | 描述 | 参数 |
|-------|-------------|------------|
| `notice` | 状态通知 | `{"code": "...", "message": "..."}` |
| `message` | 识别结果 | `{"startTime": ..., "resultText": "...", "is_final": true/false}` |

### 命令配置

```json
{
    "command": "START",
    "config": {
        "offline": false,           // true 为离线模式，false 为流式模式
        "token": "your-token",      // 可选的认证令牌
        "licenseData": "..."        // 可选的许可证数据
    }
}
```

### 识别结果格式

```json
{
    "startTime": 0,
    "endTime": 600,
    "chunkText": "",
    "resultText": "你好世界",
    "is_final": true,
    "sentenceld": 1
}
```

## 配置说明

配置文件 `config.yaml` 包含以下设置：

```yaml
BASIC:
  IS_SERVER: False        # 启用服务端模式（需要许可证）
  IS_CUDA: False         # 启用GPU加速
  OFFLINE_LIMIT_SIZE: 2  # 离线工作池最大数量
  ONLINE_LIMIT_SIZE: 0   # 在线工作池最大数量

server:
  host: 0.0.0.0          # 服务端地址
  port: 6060             # 服务端口
  origins: '*'           # CORS来源

MODEL:
  SEACO_NUM_THREADS: 4    # ASR模型线程数
  FSMN_NUM_THREADS: 1    # VAD模型线程数
  CT_NUM_THREADS: 1      # 标点模型线程数
```

## 项目结构

```
Q-PutonghuaASR-CN/
├── ASR/                    # ASR核心模块
│   ├── offline.py          # 离线ASR处理
│   ├── streaming.py        # 流式ASR处理
│   └── streaming2offline.py # 混合流式转离线
├── client/                 # 客户端组件
│   └── socket_io_client.py # Socket.IO客户端
├── flaskServer/            # Flask Web服务器
│   ├── Hs_flask_server.py  # 主Flask服务器
│   ├── web_audio_server.py # 音频文件上传处理器
│   └── flask_basicauth.py  # 基本认证
├── server/                 # 服务端组件
│   ├── asr_server.py       # ASR服务器主类
│   ├── asr_worker.py       # ASR工作进程
│   ├── session_server.py   # 会话管理
│   ├── socket_io_server.py # Socket.IO服务器
│   ├── auth_manager.py     # 认证管理器
│   └── speaker_server.py   # 扬声器服务器
├── utils/                  # 工具模块
│   ├── Config.py           # 配置加载器
│   ├── Logger.py           # 日志配置
│   ├── AudioUploadFile.py  # 文件上传处理
│   ├── HsProjectUtil.py    # 许可证工具
│   └── TestUtil.py         # 测试工具
├── test_hs/                # 测试脚本
├── weights/                # 预训练模型
├── config.yaml             # 主配置文件
├── logging.config.yaml     # 日志配置文件
├── main.py                 # 应用入口
└── asr-hotwords.txt        # 热词词典
```

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

## 版本历史

| 版本 | 描述 |
|---------|-------------|
| v1.0.0 | 初始版本，支持Socket.IO实时转写 |
| v2.0.0 | 添加HTTP文件上传和多进程处理 |
| v3.0.0 | 添加流式转离线混合模式 |

## 贡献

欢迎贡献代码！请随时提交 issue 和 pull request。

## 联系方式

如有问题或需要支持，请联系开发团队：your-email@example.com。