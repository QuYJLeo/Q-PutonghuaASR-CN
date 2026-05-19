import os
import numpy as np
import soundfile as sf
from funasr_onnx import CT_Transformer
from funasr_onnx import Fsmn_vad
from funasr_onnx import SeacoParaformer


class AsrOneFlow:
    """
    Offline ASR (Automatic Speech Recognition) flow class for batch audio processing.
    
    This class implements an offline speech recognition system that processes
    complete audio files. It integrates VAD (Voice Activity Detection), ASR
    (Automatic Speech Recognition), and punctuation models to provide complete
    speech-to-text functionality for pre-recorded audio files.
    
    Attributes:
        hot_words (str): Hot words string for boosting recognition accuracy
        asr_offline (SeacoParaformer): ONNX-based offline ASR model
        vad (Fsmn_vad): VAD model for voice activity detection
        punc (CT_Transformer): Punctuation model for text post-processing
        listener (callable): Callback function for results
        send_vad_status (bool): Flag to track VAD start status
    """

    def __init__(self, use_gpu=True, seaco_num_threads=4, fsmn_num_threads=1, ct_num_threads=1):
        """
        Initialize the offline ASR flow with pre-trained models.
        
        Args:
            use_gpu (bool): Whether to use GPU for inference (default: True)
            seaco_num_threads (int): Number of threads for SeacoParaformer model (default: 4)
            fsmn_num_threads (int): Number of threads for FSMN VAD model (default: 1)
            ct_num_threads (int): Number of threads for CT-Transformer punctuation model (default: 1)
        """
        self.hot_words = "Optional hotwords separated by spaces"

        model_dir = os.path.join(os.getcwd(), "weights", "speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch")
        self.asr_offline = SeacoParaformer(model_dir, batch_size=1, device_id="0" if use_gpu else "-1", intra_op_num_threads=seaco_num_threads)

        model_dir = os.path.join(os.getcwd(), "weights", "speech_fsmn_vad_zh-cn-16k-common-pytorch")
        self.vad = Fsmn_vad(model_dir, batch_size=1, device_id="0" if use_gpu else "-1", intra_op_num_threads=fsmn_num_threads)

        model_dir = os.path.join(os.getcwd(), "weights", "punc_ct-transformer_zh-cn-common-vocab272727-pytorch")
        self.punc = CT_Transformer(model_dir, batch_size=1, device_id="0" if use_gpu else "-1", intra_op_num_threads=ct_num_threads)

        self.listener = lambda *d: None
        self.send_vad_status = False

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

    def setListener(self, listener):
        """
        Set the callback listener for recognition results.
        
        Args:
            listener (callable): A callback function that receives recognition results.
                The function should accept a dictionary with result information.
        """
        self.listener = listener

    def flow(self, wav_path: str):
        """
        Process an audio file and perform offline speech recognition.
        
        This method loads an audio file, performs VAD to detect speech segments,
        recognizes each segment using the ASR model, adds punctuation, and sends
        results to the listener callback.
        
        Args:
            wav_path (str): Path to the WAV audio file to process
            
        Raises:
            Exception: If audio file reading fails
        """
        speech, sample_rate = sf.read(wav_path)
        if speech.shape[0] <= 0:
            raise Exception("Failed to read audio file")

        segments = self.vad(wav_path)

        if segments:
            segments = segments[0]
            for fragment in segments:
                time_stamp_start, time_stamp_end = fragment
                data = speech[int(time_stamp_start * 16):int(time_stamp_end * 16)]
                asr_res = self.asr_offline(data, self.hot_words)
                if len(asr_res) > 0:
                    asr_preds = asr_res[0]['preds']

                    try:
                        if asr_preds:
                            if not self.send_vad_status:
                                self.listener({
                                    "VadStart": time_stamp_start,
                                })
                                self.send_vad_status = True
                            final = self.punc(asr_preds)[0]
                            result = {}
                            result["final_text"] = final
                            result["time_stamp"] = {"start": time_stamp_start, "end": time_stamp_end}
                            self.listener(result)
                            self.listener({
                                "VadStop": time_stamp_end,
                            })
                            self.send_vad_status = False

                        else:
                            print("No speech text detected in active segment")
                    except:
                        continue

        self.listener({"is_over": True})