#!/usr/bin/env python3
"""Helper script to post multi-line messages to Discord via easyclaw"""
import sys
import subprocess

def main():
    if len(sys.argv) < 3:
        print("Usage: post-message.py <channel_id> <message_file>")
        sys.exit(1)
    
    channel_id = sys.argv[1]
    message_file = sys.argv[2]
    
    # Read message from file
    with open(message_file, 'r', encoding='utf-8') as f:
        message = f.read()
    
    # Call easyclaw with proper argument handling
    cmd = [
        r'C:\Program Files (x86)\easyclaw\easyclaw.exe',
        'message',
        'send',
        '--channel', 'discord',
        '--target', channel_id,
        '--message', message
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("Message posted successfully")
    else:
        print(f"Error: {result.stderr}")
        sys.exit(1)

if __name__ == '__main__':
    main()
