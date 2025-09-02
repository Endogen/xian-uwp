"""
Server utilities for robust startup and process management
"""

import socket
import psutil
import asyncio
import httpx
import logging
from typing import Optional, Tuple
from .models import ProtocolConfig

logger = logging.getLogger(__name__)


def is_port_in_use(host: str = "127.0.0.1", port: int = 8545) -> bool:
    """Check if a port is currently in use"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result == 0
    except Exception:
        return False


def find_process_using_port(port: int = 8545) -> Optional[psutil.Process]:
    """Find the process using a specific port"""
    try:
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                # Get connections for this process
                connections = proc.connections()
                if connections:
                    for conn in connections:
                        if hasattr(conn, 'laddr') and conn.laddr.port == port:
                            return psutil.Process(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except Exception as e:
        logger.debug(f"Error finding process using port {port}: {e}")
    return None


async def check_server_health(host: str = "127.0.0.1", port: int = 8545, timeout: float = 2.0) -> bool:
    """Check if the server on the given port is a healthy Xian wallet server"""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"http://{host}:{port}/api/v1/wallet/status")
            if response.status_code == 200:
                data = response.json()
                # Check if it's a Xian wallet server by looking for expected fields
                return "wallet_type" in data and "version" in data
    except Exception as e:
        logger.debug(f"Health check failed: {e}")
    return False


def kill_process_on_port(port: int = 8545, force: bool = False) -> bool:
    """Kill the process using the specified port"""
    try:
        process = find_process_using_port(port)
        if process:
            logger.info(f"Found process {process.pid} using port {port}")
            
            if force:
                # Force kill
                process.kill()
                logger.info(f"Force killed process {process.pid}")
            else:
                # Graceful termination
                process.terminate()
                logger.info(f"Terminated process {process.pid}")
                
                # Wait for process to exit
                try:
                    process.wait(timeout=3)
                except psutil.TimeoutExpired:
                    logger.warning(f"Process {process.pid} didn't exit gracefully, force killing")
                    process.kill()
            
            return True
    except Exception as e:
        logger.error(f"Error killing process on port {port}: {e}")
    return False


async def ensure_port_available(host: str = "127.0.0.1", port: int = 8545, force_cleanup: bool = False) -> Tuple[bool, str]:
    """
    Ensure the port is available for use, handling existing processes robustly
    
    Returns:
        Tuple[bool, str]: (success, message)
    """
    if not is_port_in_use(host, port):
        return True, f"Port {port} is available"
    
    logger.info(f"Port {port} is in use, checking server health...")
    
    # Check if existing server is healthy
    is_healthy = await check_server_health(host, port)
    
    if is_healthy and not force_cleanup:
        return False, f"Healthy Xian wallet server already running on port {port}"
    
    if not is_healthy:
        logger.info("Existing server is unresponsive, cleaning up...")
    else:
        logger.info("Force cleanup requested, terminating existing server...")
    
    # Try to kill the process using the port
    killed = kill_process_on_port(port, force=force_cleanup)
    
    if killed:
        # Wait a moment for the port to be released
        await asyncio.sleep(1)
        
        # Check if port is now available
        if not is_port_in_use(host, port):
            return True, f"Successfully cleaned up port {port}"
        else:
            return False, f"Port {port} still in use after cleanup attempt"
    else:
        return False, f"Failed to clean up process on port {port}"


def configure_socket_reuse():
    """Configure socket options for robust server startup"""
    # This will be used in the uvicorn configuration
    return {
        "uds": None,
        "fd": None,
        "ssl_keyfile": None,
        "ssl_certfile": None,
        "ssl_keyfile_password": None,
        "ssl_version": None,
        "ssl_cert_reqs": None,
        "ssl_ca_certs": None,
        "ssl_ciphers": None,
        "headers": [],
        "server_header": True,
        "date_header": True,
        "forwarded_allow_ips": None,
        "root_path": "",
        "limit_concurrency": None,
        "limit_max_requests": None,
        "backlog": 2048,
        "timeout_keep_alive": 5,
        "timeout_notify": 30,
        "callback_notify": None,
        "ssl": None,
        "h11_max_incomplete_event_size": None,
    }


class RobustServerManager:
    """Manager for robust server startup and shutdown"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8545):
        self.host = host
        self.port = port
        self.logger = logging.getLogger(f"{__name__}.RobustServerManager")
    
    async def prepare_startup(self, force_cleanup: bool = False) -> Tuple[bool, str]:
        """Prepare for server startup by ensuring port availability"""
        return await ensure_port_available(self.host, self.port, force_cleanup)
    
    async def graceful_shutdown_existing(self) -> bool:
        """Attempt to gracefully shutdown existing server"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Try to send shutdown signal if the server supports it
                response = await client.post(f"http://{self.host}:{self.port}/api/v1/admin/shutdown")
                if response.status_code == 200:
                    self.logger.info("Existing server acknowledged shutdown request")
                    await asyncio.sleep(2)  # Give time for graceful shutdown
                    return not is_port_in_use(self.host, self.port)
        except Exception as e:
            self.logger.debug(f"Graceful shutdown attempt failed: {e}")
        
        return False
    
    def get_startup_message(self, success: bool, message: str) -> str:
        """Get formatted startup message"""
        if success:
            return f"✅ {message}"
        else:
            return f"❌ {message}"