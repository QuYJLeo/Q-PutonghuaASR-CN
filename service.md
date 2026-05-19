# 1. FUN-ASR 在线流转写

## 1.1 command 事件说明


**监听command事件：** 

**请求格式：** JSON 字符串

**参数说明：**

| 参数             | 类型     | 必选 | 默认值 | 说明                                                         |
| ---------------- | -------- | ---- | ------ | ------------------------------------------------------------ |
| `command`        | `string` | 是   | `-`    | 值为 `START`，表示开始识别请求。 值为 `END`，表示结束识别请求。 |
| `config`         | `object` | 是   | `-`    | 配置信息对象，具体结构见下方 "config 结构说明"。             |
| `config.offline` | string   | 是   | `-`    | 值为1或者true                                                |
| `config.token`   | string   | 否   | `-`    | token 授权值                                                 |

**举例：**

```json
开始连接：{"command": "START", "config": {"offline": 1, "token": ""}}

结束连接：{"command": "END", "config": {"offline": 1, "token": ""}}
```



## 1.2 voice事件说明

**监听voice事件：** 

**请求格式：** JSON 字符串

**参数说明：**

| 参数    | 类型   | 必选 | 默认值 | 说明                                                         |
| ------- | ------ | ---- | ------ | ------------------------------------------------------------ |
| `times` | `int`  | 是   | `-`    | 当前数据的时间戳（毫秒）                                     |
| `voice` | `byte` | 是   | `-`    | voice当前的二进制音频流<span style="color:red">（**采样率16k，数据流长度尽量大于4000**）</span> |

**举例：**

```json
发送音频流，采样率16k，音频格式wav，发送的数据流长度尽量大于4000

{'times': 1768272607556, 'voice': b'P\xfe)\xfe\xbe\xfd\x90\xfd\xf9\xfdk\xfe\xa7   ......"} #太多，不写了
```



## 1.3. message事件

服务器端收到 "开始识别" 请求后，会返回如下响应消息，以 JSON 字符串形式放置在文本类型的数据帧 (text message) 中。

**参数说明：**


| 参数         | 类型      | 必选 | 说明                                                |
| ------------ | --------- | ---- | --------------------------------------------------- |
| `sentenceId` | `string`  | 是   | 句子ID，依次递增                                    |
| `startTime`  | `number`  | 是   | 一句话的起始时间戳，单位毫秒 (ms)。                 |
| `endTime`    | `number`  | 是   | 一句话的结束时间戳，单位毫秒 (ms)。                 |
| `is_final`   | `boolean` | 是   | * `true`: 最终结果。 <br> * `false`: 中间临时结果。 |
| `chunkText`  | `string`  | 是   | 块文本（临时文本，不作为最终结果）                  |
| `resultText` | `string`  | 是   | 句子文本（is_final= true: 最终结果）                |

**转写结果举例：**

```json
{'startTime': 1768270597880, 'endTime': 1768270610130, 'chunkText': '', 'resultText': '嗯，健胃消食片请仔细阅读说明书，并按说明或在药师指导下购买和使用。', 'is_final': True, 'sentenceld': 1}

{'startTime': 1768270610390, 'endTime': 1768270615130, 'chunkText': '', 'resultText': '江中药业股份有限公司。', 'is_final': True, 'sentenceld': 2}

{'startTime': 1768270616130, 'endTime': 1768270619380, 'chunkText': '', 'resultText': '健胃消食片六十四片装。', 'is_final': True, 'sentenceld': 3}
```



## 1.4 通知 notice

服务器端检测到特定事件时，返回 会发送如下响应消息，格式为 JSON 字符串

**参数说明：**

| 参数      | 类型     | 必选 | 说明                                                 |
| --------- | -------- | ---- | ---------------------------------------------------- |
| `code`    | `string` | 是   | 值为SESSION_SUCCESS（成功）或者SESSION_ERROR（失败） |
| `message` | `string` | 是   | 消息通知提示                                         |

**转写结果举例：**

```json
成功提示：{'code': 'SESSION_SUCCESS', 'message': '会话已创建'}

失败提示：{'code': 'SESSION_ERROR', 'message': '服务端连接数超限：当前10，限制10'}
```




# 2. WAV 16k 音频文件上传
## 2.1 上传接口

- **支持的音频格式**：WAV音频编码格式。
- **支持的采样率**：16k
- **是否单声道**：单声道
- **文件大小限制**：建议设置最大上传16MB限制，以防止服务器资源被大文件耗尽。
- **响应内容**：
  - `uuid` 字段是一个全局唯一的标识符，用于后续结果查询。
  - 如果上传失败，返回的 JSON 应包含错误信息。

## 2.2 查询接口

- **查询逻辑**：
  - 如果任务尚未完成，返回状态如 "processing"。
  - 如果任务完成，返回识别结果文本。
  - 如果 UUID 无效或任务不存在，返回 500错误。
- **结果格式**：
  - 结果可以是简单的纯文本，也可以包含置信度分数等详细信息。

    
## 2.3、 请求格式

## 2.3.1 请求路径

    wav音频文件上传：
    POST http(s)://ip:port/uploadAudioWav
    类似：http://192.168.1.36:6800/uploadAudioWav
    
    查询ASR结果：
    POST http(s)://ip:port/queryAudioTask
    类似：http://192.168.1.36:6800/queryAudioTask
wav音频文件上传： Form方式上传音频，wavFile配置项都放在form表单中



#### 1.4.2 上传格式

```tex
wav音频文件上传：
    请求头： Content-Type: multipart/form-data
    请求体： form-data; wavFile="audio"
    Content-Type: audio/wave

    curl --location 'http://ip:port/uploadAudioWav' \
        --form 'wavFile=@"/D:/hs/hs-ability-asr/test/audio/2.44.wav"' 

查询语音翻译结果：
    请求头： Content-Type: application/json
    请求体： {"taskId":"5ac6261f61f44c2faf18dc569de3cc8d"} 
    Content-Type: application/json

    curl --location 'http://192.168.1.36:6800/queryAudioTask' \
    	--header 'Content-Type: application/json' \
   		--data '{"taskId":"5ac6261f61f44c2faf18dc569de3cc8d"}'
```



#### 1.4.3 响应

发送识别的HTTP请求之后，会收到服务端的响应，识别的结果以JSON字符串的形式保存在该响应中。结果响应都是一样的。
成功响应 当 HTTP 状态码为 200 时，表示请求成功，识别结果在包体中。

```json
wav音频文件上传响应：
{
  "code": 0,
  "data": "fd1f9c38300b45a3874577eb10700356"  
   # uuid 字段是一个全局唯一的标识符，用于后续结果查询。 如果上传失败，返回的 JSON 应包含错误信息（如 `error` 字段）。 
}


查询语音翻译结果响应：
{
  "code": 0,
  "data": {
     "result": {
         "status ":"success",
          "text": "任何光明的未来都离不开坚实的。本来问渠哪得清如许，为有源头活水来。任何无畏的气概都源自于坚定的本来千磨万击还坚劲任尔东西南北风。而		任何卓越的成就都离不开对本来的坚守，对知识思想的叩问，对大地的扎根，对梦想的坚持。
        }
    }
}
```

发送识别的HTTP请求之后，会收到服务端的响应，识别的结果以JSON字符串的形式保存在该响应中。结果响应都是一样的。
成功响应 当 code = 0 时，表示请求成功，识别结果在包体中。


响应字段说明

| 参数         |     类型 | 说明                                      |
|:-----------|:-------:|-----------------------------------------|
| code | int | code =0 时表示服务运行正常，code=500时表示服务异常或者传入格式异常报错 |
| result     | object | 调用成功表示识别结果，调用失败时将没有此字段,多候选输出时，这里是第一候选结果 |
| result.text | string | 识别出的文本内容 |
| result.status | string | processing:正在转写，success：转写完成 |

失败响应
如果HTTP 状态码不为 200 时，表示请求失败。

失败响应示例

```json
{
    "code": 500,
    "message": "10004: Parse Task Config Failed"
}
```

