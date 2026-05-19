# Q-PutonghuaASR-CN

A high-performance Mandarin Chinese Automatic Speech Recognition (ASR) system with real-time streaming and offline processing capabilities.

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Configuration](#configuration)
- [Directory Structure](#directory-structure)
- [License](#license)

## Features

- **Real-time Streaming ASR**: Real-time speech recognition with low latency
- **Offline Batch Processing**: High-accuracy offline speech recognition
- **Hybrid Mode**: Streaming-to-offline processing for improved accuracy
- **Voice Activity Detection (VAD)**: Automatic speech segmentation
- **Punctuation Restoration**: Automatic punctuation insertion
- **Hotword Support**: Customizable hotword boosting
- **Multi-process Architecture**: Supports concurrent processing
- **WebSocket Communication**: Real-time bidirectional communication
- **Cross-platform Support**: Windows and Linux compatible

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                            │
│  [Socket.IO Client]  [HTTP Client]  [WebSocket Client]        │
└───────────────────────────┬───────────────────────────────────┘
                            │
┌───────────────────────────▼───────────────────────────────────┐
│                       Server Layer                             │
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
│  │            ASR MultiProcessWorker        │                 │
│  │  ┌─────────┐ ┌─────────┐ ┌───────────┐ │                 │
│  │  │ ASRFlow │ │AsrOneFlow││Streaming2 │ │                 │
│  │  │(Online) │ │(Offline) ││Offline    │ │                 │
│  │  └─────────┘ └─────────┘ └───────────┘ │                 │
│  └─────────────────────────────────────────┘                 │
└───────────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼───────────────────────────────────┐
│                      Model Layer                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────┐  │
│  │ SeacoParaformer │  │   FSMN-VAD      │  │CT-Transformer │  │
│  │    (ASR)        │  │ (Voice Activity)│  │ (Punctuation) │  │
│  └─────────────────┘  └─────────────────┘  └───────────────┘  │
└───────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.8+
- PyTorch 1.8+
- CUDA 10.2+ (for GPU acceleration)

### Installation

```bash
# Clone the repository
git clone https://github.com/your-repo/Q-PutonghuaASR-CN.git
cd Q-PutonghuaASR-CN

# Install dependencies
pip install -r requirements.txt

# Download pre-trained models (place in weights/ directory)
# See Model Requirements section for details
```

### Run the Server

```bash
# Start the ASR server
python main.py
```

## Installation

### Environment Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install required packages
pip install torch torchvision torchaudio
pip install funasr funasr_onnx
pip install eventlet python-socketio
pip install flask flask-basicauth
pip install psutil pyaudio
pip install librosa noisereduce
pip install cryptography pyDes
```

### Model Requirements

Download the following pre-trained models and place them in the `weights/` directory:

1. **SeacoParaformer (Offline ASR)**: `speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch`
2. **Paraformer Online**: `speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online`
3. **FSMN-VAD**: `speech_fsmn_vad_zh-cn-16k-common-pytorch`
4. **CT-Transformer (Punctuation)**: `punc_ct-transformer_zh-cn-common-vocab272727-pytorch`

## Usage

### Starting the Server

```python
from server.asr_server import AsrServer
from utils.Logger import loadLoggingConfig

# Load logging configuration
loadLoggingConfig()

# Create and start server
asr_server = AsrServer(
    host='0.0.0.0',
    port=6060,
    cors_origins='*'
)
asr_server.start()
asr_server.join()
```

### Client Example

```python
from client.socket_io_client import SocketIOClient

# Create client
client = SocketIOClient('http://localhost:6060')

# Set up event listeners
def on_message(data):
    print(f"Received: {data}")

client.setMessageListener(on_message)
client.connect()

# Send audio data
client.sendVoice(times=0, voice=audio_bytes)

# Send command
client.sendCommand({"command": "START", "config": {"offline": False}})
```

## API Documentation

### Socket.IO Events

#### Client to Server

| Event | Description | Parameters |
|-------|-------------|------------|
| `command` | Send control commands | `{"command": "START\|STOP\|END", "config": {...}}` |
| `voice` | Send audio data | `{"times": timestamp, "voice": bytes}` |

#### Server to Client

| Event | Description | Parameters |
|-------|-------------|------------|
| `notice` | Status notifications | `{"code": "...", "message": "..."}` |
| `message` | Recognition results | `{"startTime": ..., "resultText": "...", "is_final": true/false}` |

### Command Configuration

```json
{
    "command": "START",
    "config": {
        "offline": false,           // true for offline mode, false for streaming
        "token": "your-token",      // optional authentication token
        "licenseData": "..."        // optional license data
    }
}
```

### Recognition Result Format

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

## Configuration

The configuration file `config.yaml` contains the following settings:

```yaml
BASIC:
  IS_SERVER: False        # Enable server mode (requires license)
  IS_CUDA: False         # Enable GPU acceleration
  OFFLINE_LIMIT_SIZE: 2  # Max offline workers in pool
  ONLINE_LIMIT_SIZE: 0   # Max online workers in pool

server:
  host: 0.0.0.0          # Server host
  port: 6060             # Server port
  origins: '*'           # CORS origins

MODEL:
  SEACO_NUM_THREADS: 4    # Threads for ASR model
  FSMN_NUM_THREADS: 1    # Threads for VAD model
  CT_NUM_THREADS: 1      # Threads for punctuation model
```

## Directory Structure

```
Q-PutonghuaASR-CN/
├── ASR/                    # ASR core modules
│   ├── offline.py          # Offline ASR processing
│   ├── streaming.py        # Streaming ASR processing
│   └── streaming2offline.py # Hybrid streaming-to-offline
├── client/                 # Client-side components
│   └── socket_io_client.py # Socket.IO client
├── flaskServer/            # Flask web server
│   ├── Hs_flask_server.py  # Main Flask server
│   ├── web_audio_server.py # Audio file upload handler
│   └── flask_basicauth.py  # Basic authentication
├── server/                 # Server-side components
│   ├── asr_server.py       # ASR server main class
│   ├── asr_worker.py       # ASR worker process
│   ├── session_server.py   # Session management
│   ├── socket_io_server.py # Socket.IO server
│   ├── auth_manager.py     # Authentication manager
│   └── speaker_server.py   # Speaker server
├── utils/                  # Utility modules
│   ├── Config.py           # Configuration loader
│   ├── Logger.py           # Logging configuration
│   ├── AudioUploadFile.py  # File upload processing
│   ├── HsProjectUtil.py    # License utilities
│   └── TestUtil.py         # Testing utilities
├── test_hs/                # Test scripts
├── weights/                # Pre-trained models
├── config.yaml             # Main configuration
├── logging.config.yaml     # Logging configuration
├── main.py                 # Application entry point
└── asr-hotwords.txt        # Hotword dictionary
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Version History

| Version | Description |
|---------|-------------|
| v1.0.0 | Initial release with Socket.IO real-time transcription |
| v2.0.0 | Added HTTP file upload with multi-process processing |
| v3.0.0 | Added streaming-to-offline hybrid mode |

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## Contact

For support and inquiries, please contact the development team at your-email@example.com.