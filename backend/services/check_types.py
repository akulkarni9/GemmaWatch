"""
Custom check type system for different monitoring scenarios.
Supports HTTP/Web, API, DNS, and more.
"""
from enum import Enum
from typing import Dict, Any
import httpx
import socket
import json


class CheckType(str, Enum):
    """Available check types."""
    HTTP = "http"  # Full webpage monitoring (default)
    API = "api"    # REST API endpoint checks
    DNS = "dns"    # DNS resolution checks
    TCP = "tcp"    # TCP connectivity checks


class CheckConfig:
    """Configuration for a specific check type."""
    
    def __init__(self, check_type: CheckType, url: str, **options):
        self.check_type = check_type
        self.url = url
        self.timeout = options.get("timeout", 10)
        self.expected_status = options.get("expected_status", 200)
        self.headers = options.get("headers", {})
        self.method = options.get("method", "GET")
        self.body = options.get("body", None)


class CheckExecutor:
    """Execute different types of checks."""
    
    @staticmethod
    async def execute_http_check(config: CheckConfig) -> Dict[str, Any]:
        """Execute HTTP/Web page monitoring."""
        try:
            async with httpx.AsyncClient(timeout=config.timeout) as client:
                response = await client.get(config.url, headers=config.headers)
                return {
                    "status_code": response.status_code,
                    "is_success": response.status_code == config.expected_status,
                    "headers": dict(response.headers),
                    "response_time_ms": response.elapsed.total_seconds() * 1000,
                    "content_length": len(response.content)
                }
        except Exception as e:
            return {"error": str(e), "is_success": False, "status_code": 0}
    
    @staticmethod
    async def execute_api_check(config: CheckConfig) -> Dict[str, Any]:
        """Execute REST API endpoint checks."""
        try:
            async with httpx.AsyncClient(timeout=config.timeout) as client:
                if config.method == "GET":
                    response = await client.get(config.url, headers=config.headers)
                elif config.method == "POST":
                    response = await client.post(
                        config.url,
                        headers=config.headers,
                        content=config.body or ""
                    )
                else:
                    response = await client.request(config.method, config.url, headers=config.headers)
                
                try:
                    body = response.json()
                except:
                    body = response.text
                
                return {
                    "status_code": response.status_code,
                    "is_success": response.status_code == config.expected_status,
                    "response_time_ms": response.elapsed.total_seconds() * 1000,
                    "response_body": body,
                    "content_type": response.headers.get("content-type", "unknown")
                }
        except Exception as e:
            return {"error": str(e), "is_success": False, "status_code": 0}
    
    @staticmethod
    async def execute_dns_check(config: CheckConfig) -> Dict[str, Any]:
        """Execute DNS resolution checks."""
        try:
            # Extract hostname from URL
            from urllib.parse import urlparse
            hostname = urlparse(config.url).netloc or config.url
            
            # Resolve DNS
            import asyncio
            loop = asyncio.get_event_loop()
            ip = await loop.run_in_executor(None, socket.gethostbyname, hostname)
            
            return {
                "is_success": True,
                "hostname": hostname,
                "resolved_ip": ip,
                "resolution_time_ms": 0
            }
        except Exception as e:
            return {"error": str(e), "is_success": False, "hostname": config.url}
    
    @staticmethod
    async def execute_tcp_check(config: CheckConfig) -> Dict[str, Any]:
        """Execute TCP connectivity checks."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(f"http://{config.url}" if "://" not in config.url else config.url)
            host = parsed.hostname
            port = parsed.port or 80
            
            import asyncio
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=config.timeout
            )
            writer.close()
            await writer.wait_closed()
            
            return {
                "is_success": True,
                "host": host,
                "port": port,
                "connection_status": "open"
            }
        except asyncio.TimeoutError:
            return {"is_success": False, "error": "Connection timeout", "connection_status": "timeout"}
        except Exception as e:
            return {"is_success": False, "error": str(e), "connection_status": "closed"}
    
    @staticmethod
    async def execute(config: CheckConfig) -> Dict[str, Any]:
        """Execute a check based on its type."""
        if config.check_type == CheckType.HTTP:
            return await CheckExecutor.execute_http_check(config)
        elif config.check_type == CheckType.API:
            return await CheckExecutor.execute_api_check(config)
        elif config.check_type == CheckType.DNS:
            return await CheckExecutor.execute_dns_check(config)
        elif config.check_type == CheckType.TCP:
            return await CheckExecutor.execute_tcp_check(config)
        else:
            return {"error": f"Unknown check type: {config.check_type}", "is_success": False}
