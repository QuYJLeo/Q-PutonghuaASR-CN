import collections
import logging
import time
from queue import Queue, Empty

import socketio
import eventlet
import threading

_log = logging.getLogger(__name__)


class SocketIOServer:
    """
    Base Socket.IO server class for real-time communication.
    
    This class provides a foundation for building Socket.IO-based servers with
    event handling, message queuing, and connection management.
    
    Key features:
    - Event registration system
    - Message sending queue for async operations
    - Connection/disconnection handling
    - Configurable host, port, and CORS settings
    
    Attributes:
        host (str): Host address to bind
        port (int): Port to listen on
        cors_origins (str or list): CORS origins configuration
        static_files (dict): Static files configuration
        sio (socketio.Server): Socket.IO server instance
        app (socketio.WSGIApp): WSGI application wrapper
        server_thread (Thread): Server thread instance
        _running (bool): Flag to control server state
        _sendQueue (deque): Queue for outgoing messages
        _emitQueue (Queue): Queue for incoming events
    """

    def __init__(self, host='0.0.0.0', port=5000, cors_origins='*', static_files=None):
        """
        Initialize the Socket.IO server.
        
        Args:
            host (str): Host address to bind (default: '0.0.0.0')
            port (int): Port to listen on (default: 5000)
            cors_origins (str or list): Allowed CORS origins. Use '*' for all (default: '*')
            static_files (dict, optional): Static files mapping for serving web content
        """
        self.host = host
        self.port = port
        self.cors_origins = cors_origins
        self.static_files = static_files

        self.sio = socketio.Server(cors_allowed_origins=self.cors_origins,
                                   async_mode='eventlet', ping_timeout=60, ping_interval=25,
                                   max_http_buffer_size=1e7)
        if self.static_files:
            self.app = socketio.WSGIApp(self.sio, static_files=self.static_files)
        else:
            self.app = socketio.WSGIApp(self.sio)
        self.server_thread = None
        self._running = True

        self._sendQueue = collections.deque()
        self._emitQueue = Queue()

        self.register_events()

    def register_events(self):
        """Register Socket.IO event handlers."""

        @self.sio.event
        def connect(sid, environ):
            _log.debug(f"Client connected: {sid}")
            self.on_connect(sid, environ)

        @self.sio.event
        def disconnect(sid):
            _log.debug(f"Client disconnected: {sid}")
            self.on_disconnect(sid)

        @self.sio.event
        def command(sid, message):
            _log.debug(f"Received message from {sid}: {message}")
            self.on_command(sid, message.get("command"), message.get("config"))

        @self.sio.event
        def voice(sid, data):
            self._emitQueue.put(("on_voice", sid, data))

    def send(self, sid, event, message):
        """
        Send a message to a specific client.
        
        Args:
            sid (str): Session ID of the target client
            event (str): Event name
            message: Message data to send
        """
        self.sio.emit(event, message, to=sid)

    def sendNotice(self, sid, message):
        """
        Send a notice message to a client.
        
        Args:
            sid (str): Session ID of the target client
            message (dict): Notice message content
        """
        self._sendQueue.append(("notice", message, sid))

    def sendCommand(self, sid, command, config=None):
        """
        Send a command to a client.
        
        Args:
            sid (str): Session ID of the target client
            command (str): Command type
            config (dict, optional): Command configuration
        """
        data = {
            "command": command,
            "config": config
        }
        self._sendQueue.append(("command", data, sid))

    def sendMessage(self, sid, message):
        """
        Send a general message to a client.
        
        Args:
            sid (str): Session ID of the target client
            message: Message content
        """
        self._sendQueue.append(("message", message, sid))

    def on_command(self, sid, command, config):
        """
        Stub method for handling commands.
        
        Override this in subclasses to handle specific commands.
        
        Args:
            sid (str): Session ID
            command (str): Command type
            config (dict): Command configuration
        """
        ...

    def on_disconnect(self, sid):
        """
        Stub method for handling disconnections.
        
        Override this in subclasses to handle client disconnection.
        
        Args:
            sid (str): Session ID
        """
        ...

    def on_connect(self, sid, environ):
        """
        Stub method for handling connections.
        
        Override this in subclasses to handle client connection.
        
        Args:
            sid (str): Session ID
            environ (dict): Environment information
        """
        ...

    def on_voice(self, sid, data):
        """
        Stub method for handling voice data.
        
        Override this in subclasses to process incoming voice data.
        
        Args:
            sid (str): Session ID
            data (dict): Voice data
        """
        ...

    def _run_server(self):
        """Internal method to run the Socket.IO server."""
        t = threading.Thread(target=self._run_receive_message_task, name="receive_message_task_thread")
        t.start()
        self.sio.start_background_task(self._run_send_message_task)
        sock = eventlet.listen((self.host, self.port))
        eventlet.wsgi.server(sock, self.app, max_size=2048, log_output=False)

        _log.debug("Socket.IO server stopped.")

    def _run_send_message_task(self):
        """Background task to process outgoing messages."""
        _log.debug("Starting send message task")
        while True:
            while len(self._sendQueue) > 0:
                event, data, sid = self._sendQueue.popleft()
                self.sio.emit(event, data, room=sid)
            eventlet.sleep(0.01)

    def _run_receive_message_task(self):
        """Background task to process incoming messages."""
        _log.debug("Starting receive message task")
        while True:
            try:
                fun_str, sid, data = self._emitQueue.get(timeout=1)
                func = getattr(self, fun_str, None)
                if func is not None:
                    func(sid, data)
            except Empty:
                continue
            except Exception as e:
                _log.warning(f"_run_receive_message_task:{fun_str}:Exception:{e}")

    def start(self):
        """Start the Socket.IO server in a separate thread."""
        _log.debug(f"Starting Socket.IO server on {self.host}:{self.port}")
        self.server_thread = threading.Thread(target=self._run_server, daemon=True, name="SocketIOServer_Thread")
        self.server_thread.start()

    def disconnect_client(self, sid):
        """
        Disconnect a specific client.
        
        Args:
            sid (str): Session ID of the client to disconnect
        """
        self.sio.disconnect(sid)

    def join(self):
        """Wait for the server thread to complete."""
        self.server_thread.join()

    def stop(self):
        """Stop the Socket.IO server."""
        if self.server_thread and self.server_thread.is_alive():
            _log.debug("Stopping Socket.IO server...")
            _log.debug("Cannot directly stop the server thread. It will exit when the main program exits.")
        else:
            _log.debug("Socket.IO server is not running.")