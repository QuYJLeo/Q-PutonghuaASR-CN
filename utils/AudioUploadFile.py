import glob
import json
import logging
import os
import threading
import time
from concurrent.futures import ProcessPoolExecutor
from ASR.offline import AsrOneFlow
from utils.Config import PROCESS_NUM, UPLOAD_FOLDER, THRESHOLD_DAY, IS_SERVER
from utils.Config import SEACO_NUM_THREADS, FSMN_NUM_THREADS, CT_NUM_THREADS
from loguru import logger
_log = logging.getLogger(__name__)


class AudioUploadFileProcess:
    """
    Audio upload processing class for handling audio file uploads and speech recognition.
    
    This class manages audio file processing in a multi-process environment. It uses
    a process pool to handle concurrent audio file processing and provides methods
    for submitting files and cleaning up old files.
    
    Attributes:
        uploadDirname (str): Directory path for uploaded files
        _isRunning (bool): Flag to control background monitoring
        thresholdDay (int): Number of days to retain uploaded files
        _executor (ProcessPoolExecutor): Process pool for parallel processing
        monitor_loop (Thread): Background thread for file cleanup
    """

    def __init__(self):
        """Initialize the audio upload processing class."""
        self.uploadDirname = UPLOAD_FOLDER
        self._isRunning = True
        self.thresholdDay = THRESHOLD_DAY
        self._executor = ProcessPoolExecutor(max_workers=PROCESS_NUM, initializer=self.initProcess)
        self.monitor_loop = threading.Thread(target=self.background_monitor_thread, name="background_monitor_thread")
        self.monitor_loop.start()
        _log.info(f"Audio upload processing initialized, upload directory: {UPLOAD_FOLDER}, process count: {PROCESS_NUM}, file retention days: {THRESHOLD_DAY}")

    @staticmethod
    def preSubmit():
        """
        Pre-submit a test audio file to initialize the ASR model.
        
        This method loads a test audio file and runs it through the ASR model
        to ensure the model is properly initialized before processing real files.
        """
        global ASRModel
        wav_path = os.path.join(os.getcwd(), "assert", "c_cn_16k.wav")
        ASRModel.flow(wav_path=wav_path)
        logger.info(f"pid: {os.getpid()} {wav_path} preSubmit complete")

    def submit(self, file_path):
        """
        Submit an audio file to the processing queue.
        
        Args:
            file_path (str): Path to the audio file to process
        """
        self._executor.submit(self.process, file_path)

    @staticmethod
    def process(wav_path):
        """
        Process an audio file and perform ASR recognition.
        
        Args:
            wav_path (str): Path to the audio file to process
        """
        global ASRModel
        logger.info(f"Submitting file: {wav_path}")
        start = time.time()
        f = open(file=f"{wav_path}.txt", mode='w+', encoding="utf-8")
        try:
            def callback(res):
                if res.get("is_over"):
                    f.write(json.dumps({"status": "success"}, ensure_ascii=False) + "\n")
                else:
                    f.write(json.dumps(res, ensure_ascii=False) + "\n")
                f.flush()
                print(res)
            ASRModel.setListener(callback)
            ASRModel.flow(wav_path=wav_path)
        except Exception as e:
            f.write(json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False) + "\n")
        finally:
            f.flush()
            f.close()
            os.remove(wav_path)
        logger.info(f"pid {os.getpid()} {wav_path} file parsing complete, total time: {time.time() - start}")

    @staticmethod
    def initProcess():
        """
        Initialize the ASR model in each worker process.
        
        This method is called when each worker process starts to initialize
        the ASR model with the appropriate configuration.
        """
        global ASRModel
        ASRModel = AsrOneFlow(use_gpu=False, seaco_num_threads=SEACO_NUM_THREADS, fsmn_num_threads=FSMN_NUM_THREADS, ct_num_threads=CT_NUM_THREADS)
        logger.info(f"Process: {os.getpid()} initialized AsrOneFlow model")

    def background_monitor_thread(self):
        """
        Background monitoring thread for cleaning up old files.
        
        Continuously checks and deletes files older than the threshold days.
        """
        while self._isRunning:
            try:
                self.delete_files()
            except Exception as e:
                _log.warning(f"background_monitor_thread error:{e}")
            time.sleep(60 * 60)

    def delete_files(self):
        """Delete uploaded audio files that exceed the retention threshold."""
        for file_path in glob.glob(os.path.join(self.uploadDirname, '*')):
            file_mtime = os.path.getmtime(file_path)
            if time.time() - file_mtime > 60 * 60 * 24 * self.thresholdDay:
                _log.info(f"Deleting file older than threshold: {file_path}")
                os.remove(file_path)