#!/bin/bash

# Configuration
KEY="/Users/mayuri/Documents/LightsailDefaultKey-us-west-2.pem"
IP="35.89.173.248"
CHUNK_SIZE="20m" # 20MB chunks for stability

# Ensure Key Permissions
chmod 400 "$KEY"

echo "=========================================================="
echo "🚀 Starting Deployment to AWS Lightsail ($IP)"
echo "   Strategy: Compression + Micro-Chunking ($CHUNK_SIZE)"
echo "=========================================================="

UPLOAD_DATA=true
if [[ "$*" == *"--no-data"* ]]; then
    echo "ℹ️  Skipping Data Upload (--no-data flag detected)"
    UPLOAD_DATA=false
fi

# 1. Check Connection
echo "[1/7] Checking Connection..."
ssh -o StrictHostKeyChecking=no -i "$KEY" ubuntu@$IP "echo '✅ Connection Successful!'" || { echo "❌ SSH Connection Failed"; exit 1; }

# 2. Cleanup Remote
echo "[2/7] Cleaning up remote server..."
ssh -o StrictHostKeyChecking=no -i "$KEY" ubuntu@$IP "rm -rf ~/rag-agent/deploy_chunks ~/rag-agent/data_upload.tar.gz"

# 3. Compress Data
if [ "$UPLOAD_DATA" = true ]; then
    echo "[3/7] Preparing Local Data Archive..."
    mkdir -p deploy_chunks
    rm -rf deploy_chunks/*

    if [ -d "data" ]; then
        echo "      Compressing 'data/' folder..."
        tar -czf deploy_chunks/data_upload.tar.gz \
            --exclude='.DS_Store' \
            --exclude='chroma.sqlite3-journal' \
            data/
    else
        echo "❌ 'data/' directory not found!"
        exit 1
    fi

    # 4. Split
    echo "      Splitting archive into $CHUNK_SIZE chunks..."
    split -b $CHUNK_SIZE deploy_chunks/data_upload.tar.gz deploy_chunks/chunk_
else
    echo "[3/7] Skipping Data Compression..."
fi

# 5. Upload Base Code
echo "[4/7] Uploading Code & Config..."
rsync -avzP -e "ssh -o StrictHostKeyChecking=no -i $KEY" \
  --exclude 'venv' --exclude '.venv' --exclude '.git' --exclude '__pycache__' \
  --exclude '.DS_Store' --exclude 'tests' --exclude 'docs' --exclude 'All Documents' \
  --exclude 'data' \
  --exclude 'logs' \
  --exclude 'logs_from_server' \
  --exclude '*.jsonl' \
  --exclude 'deploy_chunks' \
  ./ ubuntu@$IP:~/rag-agent/

# 6. Upload Chunks Loop
if [ "$UPLOAD_DATA" = true ]; then
    echo "[5/7] Uploading Data Chunks (Robust Loop)..."
    CHUNKS=$(ls deploy_chunks/chunk_*)
    TOTAL_CHUNKS=$(ls deploy_chunks/chunk_* | wc -l | xargs)
    CURRENT=0

    # Ensure remote chunk dir exists
    ssh -o StrictHostKeyChecking=no -i "$KEY" ubuntu@$IP "mkdir -p ~/rag-agent/deploy_chunks"

    for chunk in $CHUNKS; do
        CURRENT=$((CURRENT+1))
        FILENAME=$(basename $chunk)
        echo "      Processing chunk $CURRENT/$TOTAL_CHUNKS: $FILENAME"
        
        # Retry loop for SINGLE chunk
        n=0
        uploaded=false
        until [ "$n" -ge 10 ]; do
            # Upload single file with timeout and inplace
            rsync -avP --timeout=60 --inplace -e "ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=10 -i $KEY" \
                 "$chunk" ubuntu@$IP:~/rag-agent/deploy_chunks/
                 
            if [ $? -eq 0 ]; then
                uploaded=true
                break
            fi
            
            n=$((n+1))
            echo "      ⚠️ Failed. Retrying $FILENAME in 5s (Attempt $n/10)..."
            sleep 5
        done

        if [ "$uploaded" = false ]; then
            echo "❌ Failed to upload $FILENAME after 10 attempts."
            exit 1
        fi
        # Cool down
        sleep 1
    done
else
    echo "[5/7] Skipping Data Upload..."
fi

# 7. Reassemble & Launch
if [ "$UPLOAD_DATA" = true ]; then
    echo "[6/7] Reassembling Data..."
    ssh -o StrictHostKeyChecking=no -i "$KEY" ubuntu@$IP "
      cd ~/rag-agent && 
      echo '      Stitching chunks...' &&
      cat deploy_chunks/chunk_* > data_upload.tar.gz &&
      echo '      Extracting archive...' &&
      tar -xzf data_upload.tar.gz &&
      rm -rf deploy_chunks data_upload.tar.gz &&
      echo '✅ Data extracted.'
    "
else
    echo "[6/7] Skipping Data Extraction..."
fi

echo "[7/7] Installing Docker & Starting App..."
ssh -o StrictHostKeyChecking=no -i "$KEY" ubuntu@$IP "
  sudo apt-get update -qq && 
  sudo apt-get install -y docker.io docker-compose &&
  cd ~/rag-agent && 
  sudo docker-compose down &&
  sudo docker-compose up -d --build
"

echo "=========================================================="
echo "=========================================================="
echo "=========================================================="
echo "🎉 DEPLOYMENT COMPLETE!"
echo "🌍 App is live at: https://seattlepolicyagent.duckdns.org"
echo "   (Note: Give it ~30s for the SSL certificate to generate)"
echo "=========================================================="
