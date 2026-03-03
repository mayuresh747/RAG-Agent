#!/bin/bash
KEY="/Users/mayuri/Documents/Projects/LightsailDefaultKey-us-west-2.pem"
IP="100.20.68.210"

echo "Starting robust rsync loop..."
n=0
while [ $n -lt 50 ]; do
    echo "Attempt $((n+1))/50..."
    rsync -avzP --append -e "ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=15 -i $KEY" data/ ubuntu@$IP:~/rag-agent/data/
    if [ $? -eq 0 ]; then
        echo "✅ Rsync completed successfully!"
        exit 0
    fi
    echo "⚠️ Connection dropped. Retrying in 5 seconds..."
    sleep 5
    n=$((n+1))
done
echo "❌ Failed to rsync after 50 attempts."
exit 1
