import logging
import time

import socketio
import socket

_log = logging.getLogger(__name__)


class SocketIOClient:
    """
    Socket.IO client for real-time communication with ASR server.
    
    This class provides a client implementation for connecting to an ASR server
    via Socket.IO protocol. It supports event callbacks for connection status,
    messages, commands, and notices.
    
    Attributes:
        server_url (str): URL of the Socket.IO server
        sio (socketio.Client): Socket.IO client instance
        is_connected (bool): Connection status flag
        _connectedListener (callable): Callback for connection events
        _disconnectedListener (callable): Callback for disconnection events
        _commandListener (callable): Callback for command events
        _messageListener (callable): Callback for message events
        _noticeListener (callable): Callback for notice events
    """

    def __init__(self, server_url, reconnection_attempts=0):
        """
        Initialize the Socket.IO client.
        
        Args:
            server_url (str): URL of the Socket.IO server
            reconnection_attempts (int): Number of reconnection attempts, 0 for infinite
        """
        self.server_url = server_url
        self.sio = socketio.Client(
            logger=False,
            engineio_logger=False,
            websocket_extra_options={
                'sockopt': [
                    (socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1),
                ]
            }
        )
        self.register_events()
        self.is_connected = False
        self._connectedListener = lambda *d: None
        self._disconnectedListener = lambda *d: None
        self._commandListener = lambda *d: None
        self._messageListener = lambda *d: None
        self._noticeListener = lambda *d: None

    def setConnectListener(self, listener):
        """
        Set callback for connection events.
        
        Args:
            listener (callable): Function to call when connected
        """
        self._connectedListener = listener

    def setDisconnectListener(self, listener):
        """
        Set callback for disconnection events.
        
        Args:
            listener (callable): Function to call when disconnected
        """
        self._disconnectedListener = listener

    def setCommandListener(self, listener):
        """
        Set callback for command events.
        
        Args:
            listener (callable): Function to call when a command is received
        """
        self._commandListener = listener

    def setMessageListener(self, listener):
        """
        Set callback for message events.
        
        Args:
            listener (callable): Function to call when a message is received
        """
        self._messageListener = listener

    def setNoticeListener(self, listener):
        """
        Set callback for notice events.
        
        Args:
            listener (callable): Function to call when a notice is received
        """
        self._noticeListener = listener

    def register_events(self):
        """Register Socket.IO event handlers."""

        @self.sio.event
        def connect():
            _log.debug("Connected to server")
            self.is_connected = True
            self._connectedListener()

        @self.sio.event
        def disconnect():
            _log.debug("Disconnected from server")
            self.is_connected = False
            self._disconnectedListener()

        @self.sio.event
        def command(data):
            _log.debug(f"Received command: {data}")
            self._commandListener(data)

        @self.sio.event
        def notice(notice):
            _log.debug(f"Received notice: {notice}")
            self._noticeListener(notice)

        @self.sio.event
        def message(data):
            _log.debug(f"Received message: {data}")
            self._messageListener(data)

    def connect(self):
        """
        Connect to the Socket.IO server.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.sio.connect(
                self.server_url,
                transports=['websocket', 'polling'],
                wait_timeout=10,
                retry=True
            )
            _log.debug(f"Connecting to {self.server_url}...")
        except socketio.exceptions.ConnectionError as e:
            _log.debug(f"Connection failed: {e}")
            self.is_connected = False
            return False
        return True

    def disconnect(self):
        """Disconnect from the Socket.IO server."""
        if self.is_connected:
            self.sio.disconnect()
            self.is_connected = False
            _log.debug("Disconnected from server.")
        else:
            _log.debug("Not connected to any server.")

    def send(self, event, *args):
        """
        Send a message to the server.
        
        Args:
            event (str): Event name
            *args: Message arguments
        """
        if self.is_connected:
            self.sio.emit(event, *args)
            _log.debug(f"Sent event '{event}' with args '{args}'")
        else:
            _log.warn("Not connected. Cannot send message.")

    def sendVoice(self, times, voice):
        """
        Send voice data to the server.
        
        Args:
            times (int): Timestamp in milliseconds
            voice (bytes): Raw audio data
        """
        if self.is_connected:
            data = {
                "times": times,
                "voice": voice
            }
            self.sio.emit("voice", data)
            _log.debug(f"send voice data length：{len(voice)}")
        else:
            _log.warn("Not connected. Cannot send message.")

    def sendCommand(self, command):
        """
        Send a command to the server.
        
        Args:
            command (dict): Command dictionary
        """
        if self.is_connected:
            self.sio.emit("command", command)
            _log.debug(f"Sent event 'command' with args '{command}'")
        else:
            _log.warn("Not connected. Cannot send message.")

    def sendMessage(self, message):
        """
        Send a general message to the server.
        
        Args:
            message: Message data
        """
        if self.is_connected:
            self.sio.emit("message", message)
            _log.debug(f"Sent event 'message' with args '{message}'")
        else:
            _log.warn("Not connected. Cannot send message.")

    def wait(self):
        """Block and keep the client running until manually disconnected."""
        self.sio.wait()