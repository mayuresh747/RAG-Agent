#!/bin/bash

KEY="/Users/mayuri/Documents/Projects/LightsailDefaultKey-us-west-2.pem"
IP="100.20.68.210"
LOCAL_DIR="/Users/mayuri/Documents/Projects/RAG Agent/deploy_chunks"

echo "=========================================================="
echo "🚀 Uploading Chunks to AWS ($IP) One-by-One"
echo "=========================================================="

cd "$LOCAL_DIR" || exit 1

# Get list of chunks starting with chunk_
CHUNKS=$(ls chunk_*)
TOTAL=$(echo "$CHUNKS" | wc -l | xargs)
COUNT=0

for CHUNK in $CHUNKS; do
    COUNT=$((COUNT + 1))
    echo "Uploading $CHUNK ($COUNT/$TOTAL)..."
    
    SUCCESS=false
    ATTEMPTS=0
    MAX_ATTEMPTS=5
    
    while [ "$SUCCESS" = false ] && [ $ATTEMPTS -lt $MAX_ATTEMPTS ]; do
        ATTEMPTS=$((ATTEMPTS + 1))
        
        # Use scp for the single file
        scp -o StrictHostKeyChecking=no -o ServerAliveInterval=15 -o ConnectTimeout=10 -i "$KEY" "$CHUNK" ubuntu@$IP:~/rag-agent/deploy_chunks/ > /dev/null 2>&1
        
        if [ $? -eq 0 ]; then
            # Verify file size
            LOCAL_SIZE=$(stat -f%z "$CHUNK")
            REMOTE_SIZE=$(ssh -o StrictHostKeyChecking=no -i "$KEY" ubuntu@$IP "stat -c%s ~/rag-agent/deploy_chunks/$CHUNK" 2>/dev/null)
            
            if [ "$LOCAL_SIZE" = "$REMOTE_SIZE" ]; then
                echo "✅ $CHUNK uploaded successfully."
                SUCCESS=true
            else
                echo "⚠️ Size mismatch for $CHUNK (Local: $LOCAL_SIZE, Remote: $REMOTE_SIZE). Retrying ($ATTEMPTS/$MAX_ATTEMPTS)..."
                sleep 2
            fi
        else
            echo "⚠️ Transfer failed for $CHUNK. Retrying ($ATTEMPTS/$MAX_ATTEMPTS)..."
            sleep 3
        fi
    done
    
    if [ "$SUCCESS" = false ]; then
        echo "❌ Failed to upload $CHUNK after $MAX_ATTEMPTS attempts."
        exit 1
    fi
done

echo "🎉 All chunks uploaded successfully!"
