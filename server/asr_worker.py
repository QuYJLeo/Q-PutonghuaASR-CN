import logging
import os
import threading
import time
from multiprocessing import Queue, Process
from queue import Empty

from utils.Config import SEACO_NUM_THREADS, FSMN_NUM_THREADS, CT_NUM_THREADS, IS_CUDA

_log = logging.getLogger(__name__)


def asr_process_target(input_queue, output_queue, offline: bool):
    """
    ASR processing function that runs in a child process.
    
    This function handles audio data processing in a separate process, supporting
    both online and offline modes. It communicates with the main process through
    queues for receiving audio data and sending recognition results.
    
    Args:
        input_queue (Queue): Queue for receiving audio data from the main process
        output_queue (Queue): Queue for sending recognition results back to main process
        offline (bool): True for offline mode, False for online streaming mode
    
    Note:
        - Continuously reads data from input_queue until receiving "STOP" command
        - Recognition results are automatically sent to output_queue via callback
    """
    from utils.Logger import loadLoggingConfig
    loadLoggingConfig()
    try:
        from ASR.streaming import ASRFlow
        from ASR.streaming2offline import StreamingToOffline
        d = time.perf_counter()
        if offline:
            asr_model = StreamingToOffline(IS_CUDA, SEACO_NUM_THREADS, FSMN_NUM_THREADS, CT_NUM_THREADS)
            hotwords_path = os.path.join(os.getcwd(), "asr-hotwords.txt")
            asr_model.setHotwords(hotwords_path)
        else:
            asr_model = ASRFlow()

        asr_model.setListener(lambda d: output_queue.put(d))
        asr_model.start()
        _log.info(f"ASR model loaded is_offline:{offline} IS_CUDA:{IS_CUDA} time:{time.perf_counter() - d:.2f}s PID：{os.getpid()}")
        while True:
            audio_data = input_queue.get()
            if audio_data == "STOP":
                break
            asr_model.push_data(audio_data)
        asr_model.stop()
        del asr_model
    except Exception as e:
        _log.error(f"ASR child process exception: {e}")


class ASRMultiProcessWorker:
    """
    Process handler class for ASR workers, used by AsrServer.
    
    This class manages a separate process for running ASR inference,
    providing methods to start, stop, and communicate with the worker process.
    
    Attributes:
        input_queue (Queue): Queue for sending audio data to the worker process
        output_queue (Queue): Queue for receiving results from the worker process
        asr_process (Process): The child process running ASR inference
        monitor_thread (Thread): Thread for monitoring results from output_queue
        result_callback (callable): Callback function for handling recognition results
        _running (bool): Flag to control the monitor thread
    """

    def __init__(self, is_offline):
        """
        Initialize the ASR worker.
        
        Args:
            is_offline (bool): True for offline ASR mode, False for online streaming mode
        """
        self.input_queue = Queue()
        self.output_queue = Queue()
        self.asr_process = Process(
            target=asr_process_target, args=(self.input_queue, self.output_queue, is_offline),
            daemon=True, name=f"ASRWorker-{('Offline' if is_offline else 'Online')}"
        )
        self.monitor_thread = threading.Thread(target=self._result_monitor,
                                               daemon=True,
                                               name="ASRWorkerMonitorThread")
        self.result_callback = None
        self._running = True

    def start(self):
        """Start the worker process and result monitoring thread."""
        self.asr_process.start()
        self.monitor_thread.start()

    def set_result_callback(self, callback):
        """
        Set the callback function for processing recognition results.
        
        Args:
            callback (callable): Function to handle recognition results
        """
        self.result_callback = callback

    def push_data(self, data):
        """
        Push audio data to the worker process.
        
        Args:
            data (dict): Audio data dictionary with 'times' and 'voice' keys
        """
        try:
            self.input_queue.put(data)
        except Exception as e:
            _log.warning(f"Queue push failed: {e}")

    def _result_monitor(self):
        """
        Internal result monitoring thread function.
        
        Continuously checks the output queue for results and passes them
        to the result callback if one is set.
        """
        while self._running:
            try:
                result = self.output_queue.get(timeout=0.1)
                if self.result_callback is not None:
                    self.result_callback(result)
            except Empty:
                continue
            except Exception as e:
                _log.error(f"ASRWorker result monitor exception: {e}")

    def stop(self):
        """Stop the worker process and cleanup resources."""
        try:
            pid_ = self.asr_process.pid
            self.input_queue.put("STOP")
            self._running = False
            self.asr_process.terminate()
            _log.info(f"ASRWorker PID:{pid_} stopped successfully")
        except Exception as e:
            _log.warning(f"ASRWorker stop failed:{e}")