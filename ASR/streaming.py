import os
import time
import numpy as np
import queue
import array
import threading
from funasr import AutoModel
from funasr_onnx.paraformer_online_bin import Paraformer


class ASRFlow:
    """
    Streaming ASR (Automatic Speech Recognition) flow class for real-time speech recognition.
    
    This class implements a multi-threaded streaming speech recognition system that processes
    audio data in real-time. It integrates VAD (Voice Activity Detection), ASR (Automatic
    Speech Recognition), and punctuation models to provide complete speech-to-text functionality.
    
    The class uses multiple threads to handle different stages of processing:
    - Preprocessing thread: Handles raw audio data buffering and chunking
    - VAD thread: Detects voice activity boundaries
    - Division thread: Splits audio into sentences based on VAD results
    - ASR thread: Performs speech recognition with punctuation
    
    Attributes:
        start_frame (int): Start frame index for audio processing
        end_frame (int): End frame index for audio processing
        vad_pre_idx (int): VAD pre-index for frame tracking
        frames (list): List to hold audio frames
        asr_model (Paraformer): ONNX-based ASR model
        vad_model (AutoModel): VAD model from funasr
        punc_model (AutoModel): Punctuation model from funasr
        asr_chunk_size (list): Chunk size configuration for ASR
        vad_chunk_size (int): Chunk size for VAD processing (600ms)
        chunk_stride (int): Stride between consecutive chunks (9600 samples)
        raw_data_queue (Queue): Queue for incoming raw audio data
        consume_data_queue (Queue): Queue for processed audio chunks
        rate (int): Audio sample rate (16000 Hz)
        chunk (int): Chunk size in samples (9600 = 600ms at 16kHz)
        chunk_time (int): Chunk duration in milliseconds (600ms)
        temp_data (dict): Temporary data buffer for chunk assembly
        sentenceld (int): Sentence ID counter
        chunk_start_time (int): Start time of current chunk
        sentence_start_time (int): Start time of current sentence
        text_cache (str): Cached text from partial recognition
        partial (str): Partial recognition result
        send_vad_status (bool): Flag to track VAD start status
        listener (callable): Callback function for results
        is_run (bool): Flag to control thread execution
    """

    def __init__(self):
        """Initialize the streaming ASR flow with pre-trained models."""
        self.start_frame = 0
        self.end_frame = 0
        self.vad_pre_idx = 0
        self.frames = []

        asr_model_name = os.path.join(os.getcwd(), "weights",
                                      "speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online")
        self.asr_model = Paraformer(asr_model_name, batch_size=1, quantize=True, chunk_size=[5, 10, 5],
                                    intra_op_num_threads=1)

        vad_model_name = os.path.join(os.getcwd(), "weights", "speech_fsmn_vad_zh-cn-16k-common-pytorch")
        self.vad_model = AutoModel(model=vad_model_name, disable_update=True)

        punc_model_name = os.path.join(os.getcwd(), "weights", "punc_ct-transformer_zh-cn-common-vocab272727-pytorch")
        self.punc_model = AutoModel(model=punc_model_name, disable_update=True)

        self.asr_chunk_size = [0, 10, 5]
        self.vad_chunk_size = 600
        self.chunk_stride = 9600

        self.raw_data_queue = queue.Queue(maxsize=100)
        self.consume_data_queue = queue.Queue(maxsize=100)
        self.rate = 16000
        self.chunk = 9600
        self.chunk_time = int(self.chunk / self.rate * 1000)  # 600ms
        self.temp_data = {}
        self.sentenceld = 1
        self.chunk_start_time = None
        self.sentence_start_time = None
        self.text_cache = ""
        self.partial = ""

        self.send_vad_status = False
        self.listener = lambda *d: None

        self.pre_data_thread = threading.Thread(target=self.pre_data_fun, daemon=True, name="PreprocessAudioStream")
        self.asr_infer_thread = threading.Thread(target=self.asr_infer_fun, daemon=True, name="ASRInference")

        self.sou_queue = queue.Queue()
        self.vad_queue = queue.Queue()
        self.div_queue = queue.Queue()
        self.asr_queue = queue.Queue()
        self.vad_thread = threading.Thread(target=self.runVad)
        self.div_thread = threading.Thread(target=self.runDiv)
        self.asr_thread = threading.Thread(target=self.runAsr)

        self.is_run = False

        print("Initialization completed")

    def start(self):
        """
        Start all processing threads for streaming ASR.
        
        This method starts the preprocessing, VAD, division, and ASR threads to begin
        processing incoming audio data.
        """
        self.is_run = True
        self.pre_data_thread.start()
        self.asr_infer_thread.start()
        self.vad_thread.start()
        self.div_thread.start()
        self.asr_thread.start()

    def stop(self):
        """
        Stop all processing threads and release model resources.
        
        This method stops all running threads and sets model references to None
        to free up memory.
        """
        self.is_run = False
        self.vad_thread.join()
        self.div_thread.join()
        self.asr_thread.join()
        self.pre_data_thread.join()
        self.asr_infer_thread.join()

        self.asr_on = None
        self.vad_model = None
        self.punc_model = None

    def setListener(self, listener):
        """
        Set the callback listener for recognition results.
        
        Args:
            listener (callable): A callback function that receives recognition results.
                The function should accept a dictionary with result information.
        """
        self.listener = listener

    @staticmethod
    def switch_wav_bytes(data: bytes):
        """
        Convert WAV byte data to float array.
        
        Converts raw PCM audio bytes (16-bit signed) to normalized float array.
        
        Args:
            data (bytes): Raw WAV audio data in 16-bit signed PCM format.
            
        Returns:
            np.ndarray: Normalized float array with values in range [-1.0, 1.0].
        """
        short_array = array.array("h")
        short_array.frombytes(data)
        rdata = np.array(short_array, dtype="float16") / (1 << 15)
        return rdata

    @staticmethod
    def calculate_audio_duration(byte_array, rate=16000, channels=1, bytes_per_sample=2, is_msec=True):
        """
        Calculate audio duration from byte array.
        
        Args:
            byte_array (bytes): Audio data in byte format.
            rate (int): Sample rate in Hz (default: 16000).
            channels (int): Number of audio channels (default: 1).
            bytes_per_sample (int): Bytes per audio sample (default: 2 for 16-bit).
            is_msec (bool): Return duration in milliseconds if True, seconds if False (default: True).
            
        Returns:
            float: Audio duration in milliseconds or seconds.
        """
        byte_array_length = len(byte_array)
        total_samples = byte_array_length / bytes_per_sample
        total_samples_per_channel = total_samples / channels
        duration = total_samples_per_channel / rate
        if is_msec:
            duration *= 1000
        return duration

    def push_data(self, data):
        """
        Push audio data to the processing pipeline.
        
        Args:
            data (dict): Dictionary containing audio data with keys:
                - "times": Start timestamp in milliseconds
                - "voice": Raw audio bytes in 16-bit PCM format
        """
        startTime = data["times"]  # ms
        voice = data['voice']
        duration = self.calculate_audio_duration(voice)

        voice_array = self.switch_wav_bytes(voice)

        endTime = startTime + duration
        data = {
            "startTime": startTime,
            "endTime": endTime,
            "voice_array": voice_array,
            "CHUNK": voice_array.shape[0],
            "duration": duration,
        }

        if self.sentence_start_time is None:
            self.sentence_start_time = startTime
        if self.chunk_start_time is None:
            self.chunk_start_time = startTime

        self.raw_data_queue.put(data)

    def update_temp_data(self, temp_data):
        """
        Update temporary data buffer and extract complete chunks.
        
        This method manages the temporary data buffer, extracting complete 9600-sample
        chunks when available and storing remaining data for later processing.
        
        Args:
            temp_data (dict): Dictionary containing audio chunk data with keys:
                - "startTime": Start time in milliseconds
                - "endTime": End time in milliseconds
                - "voice_array": Audio data as numpy array
                - "CHUNK": Number of samples
                - "duration": Duration in milliseconds
        """
        startTime = temp_data["startTime"]
        endTime = temp_data["endTime"]
        voice_array = temp_data["voice_array"]
        duration = temp_data["duration"]
        CHUNK = temp_data["CHUNK"]

        if CHUNK == self.chunk:
            self.consume_data_queue.put(self.temp_data.copy())
            self.temp_data.clear()
            return

        elif CHUNK > self.chunk:
            chunk_startTime = startTime
            chunk_endTime = startTime + self.chunk_time
            chunk_voice_array = voice_array[:self.chunk]
            chunk_CHUNK = self.chunk
            chunk_duration = self.chunk_time

            chunk_data = {
                "startTime": chunk_startTime,
                "endTime": chunk_startTime + 600,
                "voice_array": chunk_voice_array,
                "CHUNK": chunk_CHUNK,
                "duration": chunk_duration,
            }
            self.consume_data_queue.put(chunk_data.copy())

            self.temp_data['startTime'] = chunk_endTime
            self.temp_data['endTime'] = endTime
            self.temp_data['voice_array'] = voice_array[self.chunk:]
            self.temp_data['CHUNK'] = int(CHUNK - chunk_CHUNK)
            self.temp_data['duration'] = duration - chunk_duration

            self.update_temp_data(self.temp_data)
        else:
            return

    def pre_data_fun(self):
        """
        Preprocessing thread function.
        
        Continuously reads raw audio data from the queue, assembles it into complete
        chunks, and sends them to the processing pipeline.
        """
        while self.is_run:
            if not self.raw_data_queue.empty():
                data = self.raw_data_queue.get()
                voice_array = data["voice_array"]
                duration = data["duration"]
                CHUNK = data["CHUNK"]

                if self.temp_data:
                    temp_voice_array = self.temp_data["voice_array"]
                    temp_CHUNK = self.temp_data["CHUNK"]

                    self.temp_data["endTime"] = self.temp_data["startTime"] + duration
                    self.temp_data["voice_array"] = np.concatenate([temp_voice_array, voice_array], axis=0)
                    self.temp_data['CHUNK'] = temp_CHUNK + CHUNK
                else:
                    self.temp_data = data

                self.update_temp_data(self.temp_data)

            else:
                time.sleep(0.01)

    def runVad(self):
        """
        VAD (Voice Activity Detection) thread function.
        
        Continuously processes audio chunks to detect voice activity boundaries.
        Results are sent to the division queue for further processing.
        """
        cache = {}
        while self.is_run:
            try:
                standard_data = self.sou_queue.get(timeout=3)
                voice_array = standard_data['voice_array']

                res = self.vad_model.generate(input=voice_array, chunk_size=600, is_final=False, disable_pbar=True,
                                              cache=cache)

                self.vad_queue.put(standard_data)
                for vad_data in res[0]["value"]:
                    if vad_data[0] > 0:
                        self.div_queue.put((0, vad_data[0]))  # Start time: 0 indicates start
                    elif vad_data[1] > 0:
                        self.div_queue.put((1, vad_data[1]))  # End time: 1 indicates end
            except queue.Empty:
                time.sleep(1)

    def runDiv(self):
        """
        Division thread function.
        
        Splits audio data into sentences based on VAD results and prepares chunks
        for ASR processing. Handles buffering and chunk management.
        """
        temp_chunk = np.zeros((0,), dtype=np.float64)
        temp_start = 0
        temp_start_time = -1

        while self.is_run:
            try:
                standard_data = self.vad_queue.get(timeout=1)
                chunk = standard_data['voice_array']
                chunk_startTime = standard_data['startTime']

                if temp_start_time < 0:
                    temp_start_time = chunk_startTime

                temp_chunk = np.concatenate((temp_chunk, chunk), axis=0)

                if self.div_queue.qsize() > 0:
                    vad_status, vad_time = self.div_queue.get()
                    vad_index = vad_time * 16 - temp_start
                    if vad_status == 0:
                        temp_chunk = temp_chunk[vad_index:]
                        temp_start = vad_time * 16
                        temp_start_time = temp_start_time + int(temp_start / 16)
                    elif vad_status == 1:
                        sent_chunk = temp_chunk[:vad_index]
                        temp_chunk = temp_chunk[vad_index:]
                        temp_start = vad_time * 16
                        temp_start_time = temp_start_time + int(temp_start / 16)

                        data_length = sent_chunk.shape[0]
                        for i in range(0, data_length, 9600):
                            start_index = i
                            end_index = min(i + 9600, data_length)
                            chunk_data = sent_chunk[start_index:end_index]
                            if chunk_data.shape[0] == 9600:
                                _dic = {
                                    "startTime": temp_start_time,
                                    "endTime": temp_start_time + 600,
                                    "voice_array": chunk_data,
                                    "CHUNK": 9600,
                                }
                                self.asr_queue.put((_dic, end_index == data_length, vad_status))
                            else:
                                chunk_none = np.zeros((9600 - chunk_data.shape[0],), dtype=np.float64)
                                chunk_data = np.concatenate((chunk_data, chunk_none), axis=0)
                                _dic = {
                                    "startTime": temp_start_time,
                                    "endTime": temp_start_time + 600,
                                    "voice_array": chunk_data,
                                    "CHUNK": 9600,
                                }
                                self.asr_queue.put((_dic, True, vad_status))
                else:
                    if temp_chunk.shape[0] > 9600 * 2:
                        chunk_data = temp_chunk[:9600]
                        temp_chunk = temp_chunk[9600:]
                        temp_start += 9600
                        temp_start_time = temp_start_time + int(temp_start / 16)

                        _dic = {
                            "startTime": temp_start_time,
                            "endTime": temp_start_time + 600,
                            "voice_array": chunk_data,
                            "CHUNK": 9600,
                        }
                        self.asr_queue.put((_dic, False, 0))

            except queue.Empty:
                time.sleep(1)

    def runAsr(self):
        """
        ASR (Automatic Speech Recognition) thread function.
        
        Performs speech recognition on audio chunks and adds punctuation.
        Sends results to the listener callback.
        """
        sent_text = ""
        param_dict = {"cache": dict()}

        while self.is_run:
            try:
                standard_data, is_final, vad_status = self.asr_queue.get(timeout=1)

                chunk = standard_data['voice_array']

                param_dict["is_final"] = is_final
                rec_result = self.asr_model(audio_in=chunk, param_dict=param_dict)
                if is_final:
                    param_dict = {"cache": dict()}

                if len(rec_result) > 0:
                    if "preds" in rec_result[0]:
                        sent_text += rec_result[0]["preds"][0]

                endTime = self.chunk_start_time + 600
                result = {
                    "startTime": self.chunk_start_time,
                    "endTime": endTime,
                    "chunkText": "",
                    "resultText": sent_text,
                    'is_final': True if is_final else False,
                    "sentenceld": self.sentenceld,
                }

                if not self.send_vad_status and sent_text != "" and not is_final:
                    self.listener({
                        "VadStart": result['startTime']
                    })
                    self.send_vad_status = True

                if is_final and sent_text != "":
                    punc_res = self.punc_model.generate(input=sent_text, disable_pbar=True)
                    result['resultText'] = punc_res[0]['text']
                    result['startTime'] = self.sentence_start_time + 600 if self.sentenceld > 1 else self.sentence_start_time
                    result['endTime'] = result['endTime'] - 600

                    if not self.send_vad_status:
                        self.listener({
                            "VadStart": result['startTime'],
                        })
                        self.send_vad_status = True

                    self.sentenceld += 1
                    sent_text = ""
                    self.sentence_start_time = result['endTime']

                self.listener(result)
                if is_final and vad_status:
                    self.listener({
                        "VadStop": result['endTime'],
                    })
                    self.send_vad_status = False

                self.chunk_start_time = endTime

            except queue.Empty:
                time.sleep(1)

    def asr_infer_fun(self):
        """
        ASR inference thread function.
        
        Feeds processed audio chunks from the consume queue to the VAD processing queue.
        """
        while self.is_run:
            if not self.consume_data_queue.empty():
                standard_data = self.consume_data_queue.get()
                self.sou_queue.put(standard_data)
            else:
                time.sleep(0.01)