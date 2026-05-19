import logging
import threading
import time
from queue import Queue, Empty, Full
from typing import Optional

from server.asr_worker import ASRMultiProcessWorker
from server.session_server import SessionServer
from utils.Config import OFFLINE_LIMIT_SIZE, ONLINE_LIMIT_SIZE

_log = logging.getLogger(__name__)


class AsrServer(SessionServer):
    """
    ASR Server class that manages ASR worker instances and session lifecycle.
    
    This class extends SessionServer to provide ASR-specific functionality,
    including worker pool management, session initialization, and cleanup.
    
    Key features:
    - Worker pool management for offline and online ASR modes
    - Session lifecycle management
    - Automatic worker creation and destruction
    - Background monitoring thread for pool maintenance
    
    Attributes:
        offline_limit_size (int): Maximum number of offline workers in pool
        online_limit_size (int): Maximum number of online workers in pool
        pool_offline (Queue): Worker pool for offline ASR sessions
        pool_online (Queue): Worker pool for online ASR sessions
        all_workers (set): Set of all active worker instances
        workers_lock (Lock): Thread lock for worker set operations
        _shutdown_event (Event): Event to signal shutdown
        monitor_thread (Thread): Background thread for pool monitoring
    """

    def __init__(self, host='0.0.0.0', port=5000, cors_origins='*', static_files=None):
        """
        Initialize the ASR server with worker pools.
        
        Args:
            host (str): Host address to bind (default: '0.0.0.0')
            port (int): Port to listen on (default: 5000)
            cors_origins (str): CORS origins configuration (default: '*')
            static_files (dict): Static files configuration (default: None)
        """
        super().__init__(host, port, cors_origins, static_files)

        self.offline_limit_size = OFFLINE_LIMIT_SIZE
        self.online_limit_size = ONLINE_LIMIT_SIZE

        self.pool_offline = Queue(maxsize=self.offline_limit_size) if self.offline_limit_size > 0 else None
        self.pool_online = Queue(maxsize=self.online_limit_size) if self.online_limit_size > 0 else None

        self.all_workers = set()
        self.workers_lock = threading.Lock()

        self._shutdown_event = threading.Event()
        if self.pool_offline or self.pool_online:
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True, name="ASRPoolMonitor")
            self.monitor_thread.start()
        else:
            _log.info("[ASR-Server] Buffer pool disabled (Limit=0), running in stateless mode")

    def _create_worker(self, is_offline: bool) -> Optional[ASRMultiProcessWorker]:
        """
        Create a new ASR worker and start it.
        
        Args:
            is_offline (bool): True for offline ASR worker, False for online
            
        Returns:
            Optional[ASRMultiProcessWorker]: The created worker instance or None if failed
        """
        try:
            worker = ASRMultiProcessWorker(is_offline)
            worker.start()
            with self.workers_lock:
                self.all_workers.add(worker)
            type_str = "offline" if is_offline else "online"
            _log.debug(f"[ASR-Core] Created {type_str} Worker (PID: {worker.asr_process.pid})")
            return worker
        except Exception as e:
            _log.error(f"[ASR-Core] Failed to create Worker: {e}")
            return None

    def _safe_destroy_worker(self, worker: ASRMultiProcessWorker):
        """
        Safely destroy a worker instance.
        
        Args:
            worker (ASRMultiProcessWorker): The worker to destroy
        """
        if not worker:
            return
        try:
            pid = worker.asr_process.pid
            worker.stop()

            with self.workers_lock:
                if worker in self.all_workers:
                    self.all_workers.remove(worker)
            _log.info(f"[ASR-Core] Destroyed Worker (PID: {pid})")
        except Exception as e:
            _log.warning(f"[ASR-Core] Destroy exception: {e}")

    def _monitor_loop(self):
        """
        Background monitoring loop for worker pool maintenance.
        
        Continuously checks and fills worker pools if they have available slots.
        Runs until shutdown event is set.
        """
        _log.info(f"[ASR-Monitor] Started | offline: {self.offline_limit_size} | online: {self.online_limit_size}")
        while not self._shutdown_event.is_set():
            try:
                if self.pool_offline and not self.pool_offline.full():
                    self._fill_pool(self.pool_offline, is_offline=True)
                elif self.pool_online and not self.pool_online.full():
                    self._fill_pool(self.pool_online, is_offline=False)
            except Exception as e:
                _log.error(f"[ASR-Monitor] Loop exception: {e}")
            time.sleep(5)

    def _fill_pool(self, pool: Queue, is_offline: bool):
        """
        Add a new worker to the specified pool.
        
        Args:
            pool (Queue): The worker pool to fill
            is_offline (bool): True for offline pool, False for online
        """
        worker = self._create_worker(is_offline)
        if not worker:
            return

        try:
            pool.put(worker, block=False)
            _log.info(f"[ASR-Monitor] Added {'offline' if is_offline else 'online'} Worker to pool")
        except Full:
            _log.warning(f"[ASR-Monitor] Pool is full, discarding newly created Worker")
            self._safe_destroy_worker(worker)

    def program_receive_data(self, program, data):
        """
        Pass audio data to the ASR program.
        
        Args:
            program (ASRMultiProcessWorker): The worker instance
            data (dict): Audio data to process
        """
        if program:
            program.push_data(data)

    def initProgram(self, sid, config):
        """
        Initialize an ASR program for a new session.
        
        Attempts to get a worker from the pool, or creates a new one if pool is empty
        or disabled.
        
        Args:
            sid (str): Session ID
            config (dict): Session configuration containing 'offline' flag
            
        Returns:
            ASRMultiProcessWorker: The worker instance for this session
        """
        super().initProgram(sid, config)

        is_offline = config.get("offline", True)
        target_pool = self.pool_offline if is_offline else self.pool_online
        worker = None

        if target_pool is not None:
            try:
                worker = target_pool.get(block=False)
                _log.info(f"Session [{sid}] hit cache pool (PID: {worker.asr_process.pid})")
            except Empty:
                _log.info(f"Session [{sid}] cache pool empty, creating temporary worker")

        if worker is None:
            worker = self._create_worker(is_offline)

        if worker:
            worker.set_result_callback(callback=lambda d: self.sendMessage(sid, d))
        return worker

    def destroyProgram(self, worker):
        """
        Destroy an ASR program when session ends.
        
        Args:
            worker (ASRMultiProcessWorker): The worker instance to destroy
        """
        super().destroyProgram(worker)
        if not worker:
            return
        self._safe_destroy_worker(worker)

    def __del__(self):
        """Cleanup on program exit."""
        self._shutdown_event.set()

        with self.workers_lock:
            workers_to_kill = list(self.all_workers)

        for w in workers_to_kill:
            self._safe_destroy_worker(w)