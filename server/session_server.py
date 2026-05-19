import logging
from typing import Tuple

import eventlet

from server.auth_manager import AuthManager
from server.socket_io_server import SocketIOServer
from utils.Config import AUTHS, IS_SERVER
from utils.HsProjectUtil import HsLicenseUtil
from utils.TestUtil import testUtil

_log = logging.getLogger(__name__)


class SessionServer(SocketIOServer):
    """
    Session management server that extends SocketIOServer.
    
    This class handles client sessions, authentication, and command processing.
    It manages the lifecycle of client connections, including session creation,
    readiness tracking, and cleanup on disconnection.
    
    Attributes:
        sessions (dict): Dictionary mapping session IDs to session data
        auth (AuthManager): Authentication manager for license/token validation
    """

    def __init__(self, host='0.0.0.0', port=5000, cors_origins='*', static_files=None):
        """
        Initialize the session server.
        
        Args:
            host (str): Host address to bind (default: '0.0.0.0')
            port (int): Port to listen on (default: 5000)
            cors_origins (str): CORS origins configuration (default: '*')
            static_files (dict): Static files configuration (default: None)
        """
        super().__init__(host, port, cors_origins, static_files)
        self.sessions = {}
        self.auth = AuthManager()

    def on_connect(self, sid, environ):
        """
        Handle new client connection.
        
        Creates a new session entry for the connected client.
        
        Args:
            sid (str): Session ID
            environ (dict): Environment information from the connection
        """
        user = {
            "sid": sid,
            "isReady": False
        }
        self.sessions[sid] = user
        _log.info(f"User {sid} session created")

    def on_disconnect(self, sid):
        """
        Handle client disconnection.
        
        Destroys the session and cleans up associated resources.
        
        Args:
            sid (str): Session ID
        """
        if sid in self.sessions:
            user = self.sessions[sid]
            self.destroyProgram(user.get("program"))
            del self.sessions[sid]
            _log.info(f"User {sid} session destroyed, current session count: {self.get_ready_count()}")

    def get_ready_count(self):
        """
        Get the number of ready sessions.
        
        Returns:
            int: Number of sessions that are ready (isReady=True)
        """
        count = 0
        for sid in self.sessions:
            user = self.sessions[sid]
            if user["isReady"]:
                count += 1
        return count

    def on_voice(self, sid, data):
        """
        Handle incoming voice data from client.
        
        Passes audio data to the session's program if ready.
        
        Args:
            sid (str): Session ID
            data (dict): Audio data from client
        """
        user = self.sessions.get(sid)
        if user and user["isReady"]:
            self.program_receive_data(user["program"], data)

    def program_receive_data(self, program, data):
        """
        Stub method for passing data to the program.
        
        Override this in subclasses to handle specific program data.
        
        Args:
            program: The program instance
            data: Data to pass to the program
        """
        ...

    def initProgram(self, sid, config):
        """
        Stub method for program initialization.
        
        Override this in subclasses to initialize specific programs.
        
        Args:
            sid (str): Session ID
            config (dict): Program configuration
        """
        pass

    def destroyProgram(self, program):
        """
        Stub method for program cleanup.
        
        Override this in subclasses to clean up specific programs.
        
        Args:
            program: The program instance to destroy
        """
        ...

    def on_command(self, sid, command, config):
        """
        Handle control commands from clients.
        
        Processes START, STOP, and END commands to manage session lifecycle.
        
        Args:
            sid (str): Session ID
            command (str): Command type (START, STOP, END)
            config (dict): Command configuration
        """
        _log.info(f"Received command: {command} - config: {config}")
        ready_count = self.get_ready_count()

        if command == "START":
            success, check_content = self.auth.check_access(config, ready_count)
            if not success:
                _log.warning(f"User {sid} session creation failed! Reason: {check_content}")
                self.sendNotice(sid, {"code": "SESSION_ERROR", "message": check_content})
            else:
                user = self.sessions[sid]
                user["program"] = self.initProgram(sid, config)
                user["isReady"] = True
                self.sendNotice(sid, {"code": "SESSION_SUCCESS", "message": "Session created"})
                _log.info(f"User {sid} session creation successful! {check_content} count:{ready_count}")

        if command in ["STOP", "END"]:
            user = self.sessions[sid]
            self.destroyProgram(user.get("program"))