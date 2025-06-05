"""Integration tests for JSON protocol with real sockets."""

import socket
import threading
import time
import pytest
import json
import struct
from conductor.json_protocol import (
    send_message, 
    receive_message, 
    ProtocolError,
    MSG_PHASE, 
    MSG_RUN, 
    MSG_RESULT,
    MSG_DONE,
    MSG_ERROR,
    set_max_message_size,
    get_max_message_size,
    PROTOCOL_VERSION
)
from conductor.retval import RetVal, RETVAL_ERROR, RETVAL_DONE
from conductor.phase import Phase
from conductor.step import Step


class TestJSONProtocolIntegration:
    """Integration tests for JSON protocol with real network communication."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.server_socket = None
        self.client_socket = None
        self.server_thread = None
        self.server_data = []
        self.server_errors = []
    
    def teardown_method(self):
        """Clean up sockets and threads."""
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=1.0)
    
    def start_server(self, handler_func, port=0):
        """Start a test server on a free port."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('localhost', port))
        self.server_socket.listen(1)
        
        # Get the actual port if we used 0
        actual_port = self.server_socket.getsockname()[1]
        
        def server_thread():
            try:
                conn, addr = self.server_socket.accept()
                handler_func(conn)
                conn.close()
            except Exception as e:
                self.server_errors.append(e)
        
        self.server_thread = threading.Thread(target=server_thread)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        return actual_port
    
    def test_simple_message_exchange(self):
        """Test a simple message exchange between client and server."""
        def server_handler(conn):
            # Receive a message
            msg_type, data = receive_message(conn)
            self.server_data.append((msg_type, data))
            
            # Send a response
            send_message(conn, MSG_RESULT, {"status": "ok", "echo": data})
        
        port = self.start_server(server_handler)
        
        # Client side
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect(('localhost', port))
        
        # Send a message
        send_message(self.client_socket, MSG_RUN, {"command": "test"})
        
        # Receive response
        msg_type, data = receive_message(self.client_socket)
        
        assert msg_type == MSG_RESULT
        assert data["status"] == "ok"
        assert data["echo"] == {"command": "test"}
        
        # Check server received the correct message
        assert len(self.server_data) == 1
        assert self.server_data[0] == (MSG_RUN, {"command": "test"})
    
    def test_multiple_message_exchange(self):
        """Test multiple messages in sequence."""
        messages_received = []
        
        def server_handler(conn):
            # Receive multiple messages
            for i in range(3):
                msg_type, data = receive_message(conn)
                messages_received.append((msg_type, data))
                
                # Echo back with index
                send_message(conn, MSG_RESULT, {"index": i, "received": data})
        
        port = self.start_server(server_handler)
        
        # Client side
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect(('localhost', port))
        
        # Send multiple messages
        test_messages = [
            (MSG_PHASE, {"phase": "startup"}),
            (MSG_RUN, {"command": "echo test"}),
            (MSG_DONE, {"status": "complete"})
        ]
        
        for msg_type, data in test_messages:
            send_message(self.client_socket, msg_type, data)
        
        # Receive responses
        for i, (expected_type, expected_data) in enumerate(test_messages):
            msg_type, data = receive_message(self.client_socket)
            assert msg_type == MSG_RESULT
            assert data["index"] == i
            assert data["received"] == expected_data
        
        # Verify server received all messages
        assert messages_received == test_messages
    
    def test_large_message_handling(self):
        """Test handling of large messages near the size limit."""
        # Set a smaller limit for testing
        original_limit = get_max_message_size()
        set_max_message_size(1024 * 1024)  # 1MB
        
        try:
            def server_handler(conn):
                msg_type, data = receive_message(conn)
                # Echo back the size
                send_message(conn, MSG_RESULT, {"size": len(data["payload"])})
            
            port = self.start_server(server_handler)
            
            # Create a large payload (900KB, under the limit)
            large_payload = "x" * (900 * 1024)
            
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect(('localhost', port))
            
            send_message(self.client_socket, MSG_RUN, {"payload": large_payload})
            
            msg_type, data = receive_message(self.client_socket)
            assert msg_type == MSG_RESULT
            assert data["size"] == len(large_payload)
            
        finally:
            set_max_message_size(original_limit)
    
    def test_message_too_large_error(self):
        """Test that oversized messages are rejected."""
        # Set a very small limit
        original_limit = get_max_message_size()
        set_max_message_size(100)  # 100 bytes
        
        try:
            def server_handler(conn):
                # Try to receive the oversized message
                try:
                    receive_message(conn)
                except ProtocolError as e:
                    self.server_data.append(str(e))
            
            port = self.start_server(server_handler)
            
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect(('localhost', port))
            
            # Try to send a message larger than the limit
            large_data = {"payload": "x" * 200}
            
            # This should succeed on send (client doesn't check)
            send_message(self.client_socket, MSG_RUN, large_data)
            
            # Wait for server to process
            time.sleep(0.1)
            
            # Server should have gotten an error
            assert len(self.server_data) > 0
            assert "Message too large" in self.server_data[0]
            
        finally:
            set_max_message_size(original_limit)
    
    def test_phase_serialization_over_network(self):
        """Test sending Phase objects over the network."""
        def server_handler(conn):
            msg_type, data = receive_message(conn)
            
            # Reconstruct phase from data
            phase = Phase(data["resulthost"], data["resultport"])
            for step_data in data["steps"]:
                step = Step(
                    step_data["command"],
                    spawn=step_data.get("spawn", False),
                    timeout=step_data.get("timeout", 30)
                )
                phase.append(step)
            
            # Send back the number of steps
            send_message(conn, MSG_RESULT, {"step_count": len(phase.steps)})
        
        port = self.start_server(server_handler)
        
        # Create a phase with steps
        phase = Phase("localhost", 6971)
        phase.append(Step("echo test1"))
        phase.append(Step("spawn:sleep 1", spawn=True))
        phase.append(Step("timeout5:long_command", timeout=5))
        
        # Serialize phase data
        phase_data = {
            "resulthost": phase.resulthost,
            "resultport": phase.resultport,
            "steps": [
                {
                    "command": step.command,
                    "spawn": step.spawn,
                    "timeout": step.timeout
                }
                for step in phase.steps
            ]
        }
        
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect(('localhost', port))
        
        send_message(self.client_socket, MSG_PHASE, phase_data)
        
        msg_type, data = receive_message(self.client_socket)
        assert msg_type == MSG_RESULT
        assert data["step_count"] == 3
    
    def test_retval_serialization_over_network(self):
        """Test sending RetVal objects over the network."""
        def server_handler(conn):
            # Receive multiple RetVal-style messages
            results = []
            while True:
                msg_type, data = receive_message(conn)
                if msg_type == MSG_DONE:
                    break
                results.append((data.get("code"), data.get("message")))
            
            # Send summary
            send_message(conn, MSG_RESULT, {"total": len(results)})
        
        port = self.start_server(server_handler)
        
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect(('localhost', port))
        
        # Send several RetVal-style messages
        retvals = [
            RetVal(0, "Success"),
            RetVal(1, "Command failed"),
            RetVal(RETVAL_ERROR, "Timeout occurred"),
        ]
        
        for rv in retvals:
            send_message(self.client_socket, MSG_RESULT, {
                "code": rv.code,
                "message": rv.message
            })
        
        # Send done signal
        send_message(self.client_socket, MSG_DONE, {})
        
        # Get summary
        msg_type, data = receive_message(self.client_socket)
        assert msg_type == MSG_RESULT
        assert data["total"] == 3
    
    def test_connection_closed_handling(self):
        """Test proper handling when connection is closed."""
        def server_handler(conn):
            # Send one message then close
            send_message(conn, MSG_RESULT, {"status": "closing"})
            conn.close()
        
        port = self.start_server(server_handler)
        
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect(('localhost', port))
        
        # Receive the first message
        msg_type, data = receive_message(self.client_socket)
        assert msg_type == MSG_RESULT
        assert data["status"] == "closing"
        
        # Next receive should raise ProtocolError
        with pytest.raises(ProtocolError) as exc_info:
            receive_message(self.client_socket)
        assert "Connection closed" in str(exc_info.value)
    
    def test_invalid_protocol_version(self):
        """Test rejection of messages with wrong protocol version."""
        def server_handler(conn):
            # Manually craft a message with wrong version
            message = {
                "version": 99,  # Invalid version
                "type": MSG_RUN,
                "data": {"test": "data"}
            }
            json_bytes = json.dumps(message).encode("utf-8")
            length = struct.pack("!I", len(json_bytes))
            conn.sendall(length + json_bytes)
        
        port = self.start_server(server_handler)
        
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect(('localhost', port))
        
        # Should raise ProtocolError due to version mismatch
        with pytest.raises(ProtocolError) as exc_info:
            receive_message(self.client_socket)
        assert "Unsupported protocol version: 99" in str(exc_info.value)
    
    def test_concurrent_connections(self):
        """Test protocol with multiple concurrent connections."""
        results = []
        errors = []
        
        def client_worker(client_id, port):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(('localhost', port))
                
                # Send identification
                send_message(sock, MSG_RUN, {"client_id": client_id})
                
                # Receive response
                msg_type, data = receive_message(sock)
                results.append((client_id, data))
                
                sock.close()
            except Exception as e:
                errors.append((client_id, e))
        
        # Server that handles multiple connections
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(('localhost', 0))
        server_sock.listen(5)
        port = server_sock.getsockname()[1]
        
        def multi_server():
            for i in range(3):
                conn, addr = server_sock.accept()
                # Handle in thread
                def handle_client(conn, index):
                    msg_type, data = receive_message(conn)
                    send_message(conn, MSG_RESULT, {
                        "server_index": index,
                        "received_id": data["client_id"]
                    })
                    conn.close()
                
                t = threading.Thread(target=handle_client, args=(conn, i))
                t.start()
        
        server_thread = threading.Thread(target=multi_server)
        server_thread.daemon = True
        server_thread.start()
        
        # Start multiple clients
        threads = []
        for i in range(3):
            t = threading.Thread(target=client_worker, args=(i, port))
            threads.append(t)
            t.start()
        
        # Wait for all clients
        for t in threads:
            t.join(timeout=2.0)
        
        # Check results
        assert len(errors) == 0
        assert len(results) == 3
        
        # Each client should have received a response
        client_ids = sorted([r[0] for r in results])
        assert client_ids == [0, 1, 2]
        
        server_sock.close()