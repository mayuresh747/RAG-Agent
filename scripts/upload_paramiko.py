import paramiko
import os
import time
import sys

key_path = "/Users/mayuri/Documents/Projects/LightsailDefaultKey-us-west-2.pem"
host = "100.20.68.210"
user = "ubuntu"
local_dir = "/Users/mayuri/Documents/Projects/RAG Agent/deploy_chunks"
remote_dir = "/home/ubuntu/rag-agent/deploy_chunks"

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
        
        while True:  # Infinite retries for aggressive AWS resets
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
                print(f"❌ Failed: {e}. Reconnecting... ", end="", flush=True)
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

print("\n🎉 All chunks verified and uploaded successfully!")
sftp.close()
ssh.close()
