"""Unit tests for check types service."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.check_types import CheckType, CheckConfig, CheckExecutor


class TestCheckTypeEnum:
    """Test CheckType enumeration."""
    
    def test_check_type_values(self):
        """Test that all check types are defined."""
        assert CheckType.HTTP.value == 'http'
        assert CheckType.API.value == 'api'
        assert CheckType.DNS.value == 'dns'
        assert CheckType.TCP.value == 'tcp'
    
    def test_check_type_creation(self):
        """Test creating CheckType from string."""
        http_type = CheckType('http')
        assert http_type == CheckType.HTTP
        
        api_type = CheckType('api')
        assert api_type == CheckType.API


class TestCheckConfig:
    """Test CheckConfig class."""
    
    def test_basic_config(self):
        """Test basic configuration creation."""
        config = CheckConfig(CheckType.HTTP, 'https://example.com')
        
        assert config.check_type == CheckType.HTTP
        assert config.url == 'https://example.com'
        assert config.timeout == 10
        assert config.expected_status == 200
    
    def test_config_with_options(self):
        """Test configuration with custom options."""
        config = CheckConfig(
            CheckType.API,
            'https://api.example.com/status',
            timeout=30,
            expected_status=201,
            method='POST',
            headers={'Authorization': 'Bearer token'}
        )
        
        assert config.timeout == 30
        assert config.expected_status == 201
        assert config.method == 'POST'
        assert config.headers['Authorization'] == 'Bearer token'


class TestCheckExecutor:
    """Test CheckExecutor class."""
    
    @pytest.mark.asyncio
    async def test_http_check_success(self):
        """Test HTTP check with successful response."""
        with patch('services.check_types.httpx.AsyncClient') as mock_client:
            # Setup mock
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.elapsed.total_seconds.return_value = 0.5
            mock_response.content = b'test content'
            mock_response.headers = {'content-type': 'text/html'}
            
            mock_async_client = AsyncMock()
            mock_async_client.get = AsyncMock(return_value=mock_response)
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            
            mock_client.return_value = mock_async_client
            
            config = CheckConfig(CheckType.HTTP, 'https://example.com')
            result = await CheckExecutor.execute_http_check(config)
            
            assert result['status_code'] == 200
            assert result['is_success'] is True
            assert result['content_length'] == len(b'test content')
    
    @pytest.mark.asyncio
    async def test_http_check_failure(self):
        """Test HTTP check with error."""
        with patch('services.check_types.httpx.AsyncClient') as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.get = AsyncMock(side_effect=Exception('Connection error'))
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            
            mock_client.return_value = mock_async_client
            
            config = CheckConfig(CheckType.HTTP, 'https://example.com')
            result = await CheckExecutor.execute_http_check(config)
            
            assert result['is_success'] is False
            assert 'error' in result
    
    @pytest.mark.asyncio
    async def test_api_check_json_response(self):
        """Test API check with JSON response."""
        with patch('services.check_types.httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.elapsed.total_seconds.return_value = 0.2
            mock_response.json = MagicMock(return_value={'status': 'ok'})
            mock_response.headers = {'content-type': 'application/json'}
            
            mock_async_client = AsyncMock()
            mock_async_client.get = AsyncMock(return_value=mock_response)
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            
            mock_client.return_value = mock_async_client
            
            config = CheckConfig(
                CheckType.API,
                'https://api.example.com/status',
                method='GET'
            )
            result = await CheckExecutor.execute_api_check(config)
            
            assert result['status_code'] == 200
            assert result['is_success'] is True
            assert result['response_body'] == {'status': 'ok'}
    
    @pytest.mark.asyncio
    async def test_api_check_post_request(self):
        """Test API check with POST request."""
        with patch('services.check_types.httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.elapsed.total_seconds.return_value = 0.3
            mock_response.json = MagicMock(return_value={'id': '123'})
            mock_response.headers = {'content-type': 'application/json'}
            
            mock_async_client = AsyncMock()
            mock_async_client.post = AsyncMock(return_value=mock_response)
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            
            mock_client.return_value = mock_async_client
            
            config = CheckConfig(
                CheckType.API,
                'https://api.example.com/create',
                method='POST',
                body='{"name": "test"}',
                expected_status=201
            )
            result = await CheckExecutor.execute_api_check(config)
            
            assert result['status_code'] == 201
            assert result['is_success'] is True
    
    @pytest.mark.asyncio
    async def test_dns_check_success(self):
        """Test DNS resolution check."""
        with patch('services.check_types.socket.gethostbyname') as mock_dns:
            mock_dns.return_value = '142.251.43.46'
            
            config = CheckConfig(CheckType.DNS, 'https://google.com')
            result = await CheckExecutor.execute_dns_check(config)
            
            assert result['is_success'] is True
            assert result['hostname'] == 'google.com'
            assert result['resolved_ip'] == '142.251.43.46'
    
    @pytest.mark.asyncio
    async def test_dns_check_failure(self):
        """Test DNS check when resolution fails."""
        with patch('services.check_types.socket.gethostbyname') as mock_dns:
            mock_dns.side_effect = Exception('DNS resolution failed')
            
            config = CheckConfig(CheckType.DNS, 'https://invalid-domain-xyz123.com')
            result = await CheckExecutor.execute_dns_check(config)
            
            assert result['is_success'] is False
            assert 'error' in result
    
    @pytest.mark.asyncio
    async def test_tcp_check_success(self):
        """Test TCP connectivity check."""
        with patch('asyncio.open_connection') as mock_connect:
            mock_reader = AsyncMock()
            mock_writer = AsyncMock()
            mock_writer.wait_closed = AsyncMock()
            
            mock_connect.return_value = (mock_reader, mock_writer)
            
            config = CheckConfig(CheckType.TCP, 'google.com:80')
            result = await CheckExecutor.execute_tcp_check(config)
            
            assert result['is_success'] is True
            assert result['connection_status'] == 'open'
    
    @pytest.mark.asyncio
    async def test_tcp_check_timeout(self):
        """Test TCP check with timeout."""
        with patch('asyncio.open_connection') as mock_connect:
            import asyncio
            mock_connect.side_effect = asyncio.TimeoutError()
            
            config = CheckConfig(CheckType.TCP, 'google.com:8000', timeout=2)
            result = await CheckExecutor.execute_tcp_check(config)
            
            assert result['is_success'] is False
            assert result['connection_status'] == 'timeout'
    
    @pytest.mark.asyncio
    async def test_tcp_check_connection_refused(self):
        """Test TCP check when connection is refused."""
        with patch('asyncio.open_connection') as mock_connect:
            mock_connect.side_effect = ConnectionRefusedError()
            
            config = CheckConfig(CheckType.TCP, 'localhost:9999')
            result = await CheckExecutor.execute_tcp_check(config)
            
            assert result['is_success'] is False
            assert result['connection_status'] == 'closed'
    
    @pytest.mark.asyncio
    async def test_execute_router_http(self):
        """Test execute router with HTTP check type."""
        with patch.object(CheckExecutor, 'execute_http_check') as mock_http:
            mock_http.return_value = {'is_success': True, 'status_code': 200}
            
            config = CheckConfig(CheckType.HTTP, 'https://example.com')
            result = await CheckExecutor.execute(config)
            
            assert result['is_success'] is True
            mock_http.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_router_api(self):
        """Test execute router with API check type."""
        with patch.object(CheckExecutor, 'execute_api_check') as mock_api:
            mock_api.return_value = {'is_success': True, 'status_code': 200}
            
            config = CheckConfig(CheckType.API, 'https://api.example.com')
            result = await CheckExecutor.execute(config)
            
            assert result['is_success'] is True
            mock_api.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_router_dns(self):
        """Test execute router with DNS check type."""
        with patch.object(CheckExecutor, 'execute_dns_check') as mock_dns:
            mock_dns.return_value = {'is_success': True, 'resolved_ip': '1.2.3.4'}
            
            config = CheckConfig(CheckType.DNS, 'example.com')
            result = await CheckExecutor.execute(config)
            
            assert result['is_success'] is True
            mock_dns.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_router_tcp(self):
        """Test execute router with TCP check type."""
        with patch.object(CheckExecutor, 'execute_tcp_check') as mock_tcp:
            mock_tcp.return_value = {'is_success': True, 'connection_status': 'open'}
            
            config = CheckConfig(CheckType.TCP, 'example.com:80')
            result = await CheckExecutor.execute(config)
            
            assert result['is_success'] is True
            mock_tcp.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_unknown_type(self):
        """Test execute with unknown check type."""
        # Create config with unknown type by manipulating directly
        config = CheckConfig(CheckType.HTTP, 'https://example.com')
        config.check_type = 'unknown'  # Invalid type
        
        result = await CheckExecutor.execute(config)
        
        assert result['is_success'] is False
        assert 'error' in result
