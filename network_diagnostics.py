#!/usr/bin/env python3
"""
Network diagnostics to check if controller can receive messages from rig.
"""

import socket
import time
import threading
import zmq
import json
from neurpi.prefs import configure_prefs


def test_controller_ports():
    """Test if controller ports are actually listening."""
    print("🔍 Testing controller port availability...")
    
    controller_ip = "10.155.204.229"
    msg_port = 12000
    push_port = 12000
    
    for port_name, port in [("MSGPORT", msg_port), ("PUSHPORT", push_port)]:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((controller_ip, port))
            
            if result == 0:
                print(f"✅ {port_name} {port}: OPEN - Controller is listening")
            else:
                print(f"❌ {port_name} {port}: CLOSED - Controller not listening or blocked")
                
            sock.close()
        except Exception as e:
            print(f"❌ {port_name} {port}: ERROR - {e}")


def test_zmq_connection():
    """Test ZMQ connection to controller."""
    print("\n🔍 Testing ZMQ connection to controller...")
    
    try:
        context = zmq.Context()
        
        # Test DEALER socket (like rig uses)
        dealer = context.socket(zmq.DEALER)
        dealer.setsockopt(zmq.IDENTITY, b"test_rig")
        dealer.setsockopt(zmq.LINGER, 0)
        dealer.connect("tcp://10.155.204.229:12000")
        
        # Send a test message
        test_msg = {
            "to": "T",
            "sender": "test_rig", 
            "key": "HANDSHAKE",
            "value": {"rig": "test_rig", "ip": "127.0.0.1", "state": "IDLE"}
        }
        
        print("📤 Sending test handshake message...")
        dealer.send_json(test_msg)
        
        # Try to receive acknowledgment
        print("👂 Waiting for response...")
        if dealer.poll(5000):  # 5 second timeout
            response = dealer.recv()
            print(f"✅ Received response: {response}")
        else:
            print("❌ No response received within 5 seconds")
            
        dealer.close()
        context.term()
        
    except Exception as e:
        print(f"❌ ZMQ test failed: {e}")


def sniff_network_traffic():
    """Simple network sniffer to see if packets are reaching controller."""
    print("\n🔍 Testing raw network connectivity...")
    
    try:
        # Test ping to controller
        import subprocess
        result = subprocess.run(
            ["ping", "-c", "3", "10.155.204.229"], 
            capture_output=True, 
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("✅ Ping to controller successful")
        else:
            print(f"❌ Ping to controller failed: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Ping test failed: {e}")


def check_controller_logs():
    """Check if controller logs show any issues."""
    print("\n🔍 Checking controller logs...")
    
    import os
    log_file = "/home/pi1/Documents/NeuRPi/logs/agents.controller.log"  # Adjust path as needed
    
    if os.path.exists(log_file):
        print(f"📁 Reading last 20 lines of {log_file}...")
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
                for line in lines[-20:]:
                    print(f"  {line.strip()}")
        except Exception as e:
            print(f"❌ Could not read log file: {e}")
    else:
        print(f"❌ Log file not found: {log_file}")


def main():
    """Run all network diagnostics."""
    print("🚀 NeuRPi Network Diagnostics")
    print("=" * 50)
    
    test_controller_ports()
    test_zmq_connection()
    sniff_network_traffic()
    check_controller_logs()
    
    print("\n" + "=" * 50)
    print("🔧 TROUBLESHOOTING STEPS:")
    print("1. Check if controller is actually running and listening")
    print("2. Check firewall settings on controller machine")
    print("3. Verify both machines are on same network")
    print("4. Check controller logs for any startup errors")
    print("5. Try restarting controller with DEBUG logging")


if __name__ == "__main__":
    main()
