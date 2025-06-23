#!/usr/bin/env python3
"""
Test ZMQ connection to controller
"""

import zmq
import time

def test_controller_connection():
    print("🔧 Testing ZMQ connection to controller...")
    
    # Test if controller is listening on the router socket
    context = zmq.Context()
    socket = context.socket(zmq.DEALER)
    socket.setsockopt_string(zmq.IDENTITY, 'test_client')
    socket.setsockopt(zmq.LINGER, 0)

    try:
        socket.connect('tcp://10.155.204.229:12000')
        print('✓ Connected to controller router socket')
        
        # Send a test message
        socket.send_multipart([b'T', b'TEST_MESSAGE', b'Hello Controller'])
        print('✓ Test message sent')
        
        # Try to receive (with timeout)
        if socket.poll(timeout=2000):
            response = socket.recv_multipart()
            print(f'✓ Received: {response}')
        else:
            print('⚠️ No response (might be normal if controller not running)')
            
    except Exception as e:
        print(f'❌ Connection failed: {e}')
    finally:
        socket.close()
        context.term()

if __name__ == "__main__":
    test_controller_connection()
