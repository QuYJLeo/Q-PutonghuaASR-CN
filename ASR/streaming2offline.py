import queue
import threading
import time
import array
import os
import numpy as np
from funasr_onnx import Fsmn_vad_online, SeacoParaformer, CT_Transformer
import noisereduce as nr
import librosa


class StreamingToOffline:
    """
    Streaming to Offline ASR flow class.
    
    This class implements a hybrid speech recognition system that processes
    streaming audio data but performs offline-style recognition on detected
    speech segments. It combines VAD (Voice Activity Detection) for segmenting
    speech from audio stream and offline ASR for high-accuracy recognition.
    
    Key features:
    - Real-time streaming audio processing
    - Online VAD for speech detection
    - Offline ASR for higher accuracy recognition
    - Optional noise reduction
    - Hotword support
    
    Attributes:
        hot_words (str): Hot words string for boosting recognition accuracy
        asr_offline (SeacoParaformer): ONNX-based offline ASR model
        vad_model (Fsmn_vad_online): Online VAD model
        punc_model (CT_Transformer): Punctuation model
        raw_data_queue (Queue): Queue for incoming raw audio data
        rate (int): Audio sample rate (16000 Hz)
        temp_data (dict): Temporary data buffer
        sentenceld (int): Sentence ID counter
        listener (callable): Callback function for results
        is_run (bool): Flag to control thread execution
        start_frame (int): Start frame index
        end_frame (int): End frame index
        vad_pre_idx (int): VAD pre-index for frame tracking
        frames (list): List to hold audio frames
        current_start_time (int): Current speech segment start time
        current_stop_time (int): Current speech segment stop time
        is_denoise (bool): Flag for noise reduction
        run_time (int): Processing run time
        send_vad_status (bool): Flag to track VAD start status
        noise (np.ndarray): Noise profile for denoising
    """

    def __init__(self, use_gpu=True, seaco_num_threads=1, fsmn_num_threads=1, ct_num_threads=1, is_denoise=True):
        """
        Initialize the streaming-to-offline ASR flow with pre-trained models.
        
        Args:
            use_gpu (bool): Whether to use GPU for inference (default: True)
            seaco_num_threads (int): Number of threads for SeacoParaformer model (default: 1)
            fsmn_num_threads (int): Number of threads for FSMN VAD model (default: 1)
            ct_num_threads (int): Number of threads for CT-Transformer punctuation model (default: 1)
            is_denoise (bool): Enable noise reduction (default: True)
        """
        self.hot_words = "Optional hotwords separated by spaces"
        model_dir = os.path.join(os.getcwd(), "weights", "speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch")
        self.asr_offline = SeacoParaformer(model_dir,
                                           batch_size=1,
                                           device_id="0" if use_gpu else "-1",
                                           intra_op_num_threads=seaco_num_threads)

        model_dir = os.path.join(os.getcwd(), "weights", "speech_fsmn_vad_zh-cn-16k-common-pytorch")
        self.vad_model = Fsmn_vad_online(model_dir,
                                         batch_size=1,
                                         device_id="0" if use_gpu else "-1",
                                         intra_op_num_threads=fsmn_num_threads)

        model_dir = os.path.join(os.getcwd(), "weights", "punc_ct-transformer_zh-cn-common-vocab272727-pytorch")
        self.punc_model = CT_Transformer(model_dir,
                                         batch_size=1,
                                         device_id="0" if use_gpu else "-1",
                                         intra_op_num_threads=ct_num_threads)

        self.raw_data_queue = queue.Queue()
        self.rate = 16000
        self.temp_data = {}
        self.sentenceld = 1
        self.listener = lambda *d: None
        self.is_run = False
        self.start_frame = 0
        self.end_frame = 0
        self.vad_pre_idx = 0
        self.frames = []
        self.current_start_time = None
        self.current_stop_time = None
        self.is_denoise = False
        self.run_time = None
        self.send_vad_status = False
        if self.is_denoise:
            self.noise, _ = librosa.load(os.path.join(os.getcwd(), "assert", "noise.wav"), sr=self.rate)
            print("Noise reduction enabled")
        self._thread = threading.Thread(target=self.core)

        print("Initialization completed")

    def setHotwords(self, hot_words_path: str):
        """
        Load hotwords from a text file to boost recognition accuracy.
        
        Args:
            hot_words_path (str): Path to a text file containing hotwords, one per line
        """
        hws = []
        assert hot_words_path.endswith(".txt")
        with open(hot_words_path, "r", encoding="utf-8") as f:
            contexts = f.readlines()
            for line in contexts:
                hws.append(line.strip())
        self.hot_words = " ".join(hws)
        del hws

    def start(self):
        """Start the processing thread."""
        self.is_run = True
        self._thread.start()

    def stop(self):
        """Stop the processing thread and release model resources."""
        self.is_run = False
        self._thread.join()

        self.asr_offline = None
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
        startTime = data["times"]
        voice = data['voice']
        duration = self.calculate_audio_duration(voice)

        voice_array = self.switch_wav_bytes(voice)

        endTime = startTime + int(duration)
        data = {
            "startTime": startTime,
            "endTime": endTime,
            "voice_array": voice_array,
            "CHUNK": voice_array.shape[0],
            "duration": duration,
        }

        self.raw_data_queue.put(data)

    def core(self):
        """
        Main processing thread function.
        
        Continuously processes audio data from the queue, performs VAD to detect
        speech segments, and runs offline ASR on complete segments. Results are
        sent to the listener callback.
        """
        cache = dict()
        cache['in_cache'] = []
        cache["is_final"] = False

        while self.is_run:
            try:
                standard_data = self.raw_data_queue.get(timeout=3)
                voice_array = standard_data['voice_array']
                if self.is_denoise:
                    voice_array = nr.reduce_noise(y=voice_array, sr=self.rate, y_noise=self.noise)

                self.frames.extend(voice_array.tolist())
                self.vad_pre_idx += len(voice_array)

                res = self.vad_model(audio_in=voice_array, param_dict=cache)
                if len(res) > 0:
                    for vad_data in res[0]:
                        start, end = vad_data
                        if start != -1:
                            self.speech_start = True
                            if not self.send_vad_status:
                                self.listener({
                                    "VadStart": standard_data['startTime'],
                                })
                            self.current_start_time = standard_data['startTime']

                            self.start_frame = start * 16
                            frame_start_num = self.start_frame + len(self.frames) - self.vad_pre_idx
                            self.frames = self.frames[frame_start_num:]

                        if end != -1:
                            self.speech_start = False
                            self.current_stop_time = standard_data['endTime']
                            self.end_frame = end * 16
                            frame_end_num = self.end_frame + len(self.frames) - self.vad_pre_idx
                            data = np.array(self.frames[:frame_end_num])
                            self.frames = self.frames[frame_end_num:]
                            asr_offline_final = self.asr_offline(data, self.hot_words)

                            result = {
                                "startTime": self.current_start_time,
                                "endTime": self.current_stop_time,
                                "chunkText": "",
                                "resultText": "",
                                'is_final': True,
                                "sentenceld": self.sentenceld,
                            }

                            if len(asr_offline_final) > 0:
                                asr_preds = asr_offline_final[0]['preds']
                                if asr_preds:
                                    final = self.punc_model(asr_preds)[0]
                                    result['resultText'] = final
                                    self.sentenceld += 1
                                    self.listener(result)
                                    self.listener({
                                        "VadStop": result['endTime'],
                                    })
                                    self.send_vad_status = False

            except queue.Empty:
                time.sleep(1)