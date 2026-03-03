import argparse
import paramiko
import os
import time
import sys

# ── CLI Arguments ────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Upload deploy chunks to AWS via SFTP")
parser.add_argument("--ip", default=os.environ.get("DEPLOY_IP"), help="Server IP (or set DEPLOY_IP env var)")
parser.add_argument("--key", default=os.environ.get("DEPLOY_KEY"), help="SSH key path (or set DEPLOY_KEY env var)")
parser.add_argument("--user", default="ubuntu", help="SSH username (default: ubuntu)")
parser.add_argument("--local-dir", default=None, help="Local chunks directory")
parser.add_argument("--remote-dir", default="/home/ubuntu/rag-agent/deploy_chunks", help="Remote chunks directory")
parser.add_argument("--max-retries", type=int, default=20, help="Max retries per chunk (default: 20)")
args = parser.parse_args()

host = args.ip
key_path = args.key
user = args.user
remote_dir = args.remote_dir
max_retries = args.max_retries

if not host or not key_path:
    print("❌ Error: Server IP and SSH key path are required.")
    print("   Use --ip and --key flags, or set DEPLOY_IP and DEPLOY_KEY env vars.")
    sys.exit(1)

# Default local dir relative to script location
local_dir = args.local_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "deploy_chunks")

print(f"Connecting to {host}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(host, username=user, key_filename=key_path, timeout=60, banner_timeout=60, auth_timeout=60)
    transport = ssh.get_transport()
    transport.set_keepalive(15)
    print("✅ Connected!")
except Exception as e:
    print(f"❌ Connection failed: {e}")
    sys.exit(1)

ssh.exec_command(f"mkdir -p {remote_dir}")

def get_sftp(ssh_client):
    sftp_client = ssh_client.open_sftp()
    sftp_client.get_channel().settimeout(120)
    return sftp_client

sftp = get_sftp(ssh)

chunks = [f for f in os.listdir(local_dir) if f.startswith('chunk_')]
chunks.sort()

total = len(chunks)
print(f"Found {total} chunks to upload.")

for i, chunk in enumerate(chunks, 1):
    local_path = os.path.join(local_dir, chunk)
    remote_path = f"{remote_dir}/{chunk}"
    
    local_size = os.path.getsize(local_path)
    need_upload = True
    
    try:
        remote_stat = sftp.stat(remote_path)
        if remote_stat.st_size == local_size:
            print(f"⏩ {chunk} ({i}/{total}) already exists and size matches. Skipping.")
            need_upload = False
    except IOError:
        pass
        
    if need_upload:
        print(f"⬆️ Uploading {chunk} ({i}/{total})... ", end="", flush=True)
        
        for attempt in range(1, max_retries + 1):
            try:
                # Check how much is already uploaded to resume
                remote_size = 0
                try:
                    remote_size = sftp.stat(remote_path).st_size
                except IOError:
                    pass
                
                if remote_size == local_size:
                    print("✅ Done!")
                    break
                elif remote_size > local_size:
                    # Corrupt, start over
                    sftp.remove(remote_path)
                    remote_size = 0
                
                if remote_size > 0:
                    print(f"[Resuming from {remote_size}]... ", end="", flush=True)

                # Open local and remote files, seek to remote_size, and copy the rest
                with open(local_path, 'rb') as local_file:
                    local_file.seek(remote_size)
                    with sftp.open(remote_path, 'ab') as remote_file:
                        remote_file.set_pipelined(True)
                        while True:
                            data = local_file.read(32768) # 32KB chunks
                            if not data:
                                break
                            remote_file.write(data)
                
                # Verify size after loop
                if sftp.stat(remote_path).st_size == local_size:
                    print("✅ Done!")
                    break
                    
            except Exception as e:
                print(f"❌ Failed (attempt {attempt}/{max_retries}): {e}. Reconnecting... ", end="", flush=True)
                time.sleep(3)
                try:
                    sftp.close()
                except: pass
                
                try:
                    ssh.close()
                except: pass
                
                try:
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(host, username=user, key_filename=key_path, timeout=60)
                    ssh.get_transport().set_keepalive(15)
                    sftp = get_sftp(ssh)
                except Exception as reconnect_err:
                    print(f"Reconnect failed: {reconnect_err}")
        else:
            print(f"\n❌ FATAL: Failed to upload {chunk} after {max_retries} attempts. Aborting.")
            sftp.close()
            ssh.close()
            sys.exit(1)

print("\n🎉 All chunks verified and uploaded successfully!")
sftp.close()
ssh.close()
