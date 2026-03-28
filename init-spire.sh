#!/bin/bash

echo "--- 1. Generating Join Token for Agent ---"
TOKEN=$(docker compose exec spire-server /opt/spire/bin/spire-server token generate -spiffeID spiffe://blog.local/agent-poc | grep "Token:" | awk '{print $2}')

if [ -z "$TOKEN" ]; then
    echo "Error: Could not generate token."
    exit 1
fi

echo "Token generated: $TOKEN"

echo "--- 2. Registering Workloads in SPIRE Server ---"

# Registration of Agent A
docker compose exec spire-server /opt/spire/bin/spire-server entry create \
    -parentID spiffe://blog.local/agent-poc \
    -spiffeID spiffe://blog.local/agent_a \
    -selector docker:label:app:agent_a

# Registration of Agent B
docker compose exec spire-server /opt/spire/bin/spire-server entry create \
    -parentID spiffe://blog.local/agent-poc \
    -spiffeID spiffe://blog.local/agent_b \
    -selector docker:label:app:agent_b \
    -dns agent-b-server

echo "--- Registration Complete ---"