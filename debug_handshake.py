#!/usr/bin/env python3
"""
Debug script for handshake communication between rig and controller.
Run this to test if handshake messages are being sent and received properly.
"""

import os
import sys
import time
import threading
from pathlib import Path

# Add NeuRPi to path
sys.path.insert(0, str(Path(__file__).parent))

from neurpi.prefs import configure_prefs


def test_rig_handshake():
    """Test rig handshake functionality."""
    print("🔧 Testing rig handshake...")

    try:
        # Configure for rig mode
        configure_prefs(mode="rig")
        from neurpi.agents.rig import Rig

        print("✓ Creating rig instance...")
        rig = Rig()

        print(f"✓ Rig created: name={rig.name}, ip={rig.ip}, state={rig.state}")
        print(f"✓ Parent ID: {rig.parentid}")

        # Manual handshake test
        print("🤝 Sending handshake...")
        rig.handshake()

        # Wait a bit for potential response
        time.sleep(2)

        print("✓ Handshake test completed")

    except Exception as e:
        print(f"❌ Rig handshake test failed: {e}")
        import traceback
        traceback.print_exc()


def test_controller_listening():
    """Test controller handshake listening."""
    print("🔧 Testing controller handshake listening...")

    try:
        # Configure for controller mode
        configure_prefs(mode="controller")
        from neurpi.agents.controller import Controller

        print("✓ Creating controller instance...")
        controller = Controller()

        print(f"✓ Controller created, rigs: {list(controller.rigs.keys())}")

        # Let it run for a few seconds to receive handshakes
        print("👂 Listening for handshakes for 5 seconds...")
        time.sleep(5)

        print(f"✓ Final rig count: {len(controller.rigs)}")
        for rig_name, rig_info in controller.rigs.items():
            print(f"  - {rig_name}: {rig_info}")

        print("✓ Controller test completed")

    except Exception as e:
        print(f"❌ Controller test failed: {e}")
        import traceback
        traceback.print_exc()


def test_network_connectivity():
    """Test basic network connectivity."""
    print("🔧 Testing network connectivity...")

    try:
        # Test basic socket connection
        import socket
        import neurpi.prefs as prefs

        controller_ip = prefs.get("CONTROLLERIP")
        msg_port = prefs.get("MSGPORT")
        push_port = prefs.get("PUSHPORT")

        print(f"Controller IP: {controller_ip}")
        print(f"Message Port: {msg_port}")
        print(f"Push Port: {push_port}")

        # Test if we can connect to controller
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)

        try:
            result = sock.connect_ex((controller_ip, push_port))
            if result == 0:
                print("✓ Can connect to controller push port")
            else:
                print(f"❌ Cannot connect to controller push port: {result}")
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
        finally:
            sock.close()

        # Test ZMQ connection specifically
        print("\n🔧 Testing ZMQ connection...")
        import zmq
        
        context = zmq.Context()
        dealer = context.socket(zmq.DEALER)
        dealer.setsockopt_string(zmq.IDENTITY, "test_rig")
        dealer.setsockopt(zmq.LINGER, 0)
        
        try:
            dealer.connect(f"tcp://{controller_ip}:{push_port}")
            print(f"✓ ZMQ DEALER connected to tcp://{controller_ip}:{push_port}")
            
            # Send a test message
            test_msg = ["TEST", "HANDSHAKE", '{"test": "data"}']
            dealer.send_multipart([part.encode() if isinstance(part, str) else part for part in test_msg])
            print("✓ Test message sent")
            
            # Try to receive response (with timeout)
            if dealer.poll(timeout=2000):  # 2 second timeout
                response = dealer.recv_multipart()
                print(f"✓ Received response: {response}")
            else:
                print("⚠️ No response received (timeout)")
                
        except Exception as e:
            print(f"❌ ZMQ connection test failed: {e}")
        finally:
            dealer.close()
            context.term()

    except Exception as e:
        print(f"❌ Network test failed: {e}")


def test_zmq_handshake():
    """Test ZMQ handshake specifically."""
    print("🔧 Testing ZMQ handshake simulation...")
    
    try:
        import zmq
        import json
        from neurpi.prefs import configure_prefs
        
        # Get config
        configure_prefs(mode="rig")
        from neurpi.prefs import prefs
        
        controller_ip = prefs.get("CONTROLLERIP")
        push_port = prefs.get("PUSHPORT")
        rig_name = prefs.get("NAME")
        
        print(f"Simulating handshake from {rig_name} to {controller_ip}:{push_port}")
        
        context = zmq.Context()
        dealer = context.socket(zmq.DEALER)
        dealer.setsockopt_string(zmq.IDENTITY, rig_name)
        dealer.setsockopt(zmq.LINGER, 0)
        
        try:
            dealer.connect(f"tcp://{controller_ip}:{push_port}")
            print("✓ Connected")
            
            # Create handshake message in the same format as the real rig
            handshake_data = {
                "rig": rig_name,
                "ip": "127.0.0.1",  # Test IP
                "state": "IDLE",
                "prefs": {"test": "data"}
            }
            
            # Send message in the format expected by ControllerStation
            message_parts = [
                b"T",  # TO
                b"HANDSHAKE",  # KEY  
                json.dumps(handshake_data).encode()  # VALUE
            ]
            
            dealer.send_multipart(message_parts)
            print(f"✓ Sent handshake: {handshake_data}")
            
            # Wait for response
            if dealer.poll(timeout=3000):
                response = dealer.recv_multipart()
                print(f"✓ Received: {response}")
            else:
                print("⚠️ No response (this might be expected)")
                
        except Exception as e:
            print(f"❌ ZMQ handshake test failed: {e}")
        finally:
            dealer.close()
            context.term()
            
    except Exception as e:
        print(f"❌ Handshake simulation failed: {e}")


def main():
    """Main diagnostic function."""
    print("🚀 NeuRPi Handshake Diagnostic Tool")
    print("=" * 50)

    # Parse command line arguments
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    else:
        mode = input("Test mode (rig/controller/network/zmq): ").lower()

    if mode == "rig":
        test_rig_handshake()
    elif mode == "controller":
        test_controller_listening()
    elif mode == "network":
        test_network_connectivity()
    elif mode == "zmq":
        test_zmq_handshake()
    else:
        print("Running all tests...")
        test_network_connectivity()
        print("\n" + "=" * 50)
        test_zmq_handshake()
        print("\n" + "=" * 50)
        test_rig_handshake()
        print("\n" + "=" * 50)
        test_controller_listening()


if __name__ == "__main__":
    main()
