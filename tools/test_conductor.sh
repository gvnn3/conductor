#!/bin/bash

# Test script for conductor localhost example

echo "Starting Conductor localhost test..."
echo "=================================="

# Change to the test directory
cd tests/localhost

# Start the player in background
echo "Starting player on localhost..."
../../venv/bin/player dut.cfg &
PLAYER_PID=$!

# Give player time to start listening
sleep 2

# Run the conductor
echo "Starting conductor..."
../../venv/bin/conduct conductor.cfg

# Wait a bit for any final output
sleep 1

# Kill the player
echo "Stopping player..."
kill $PLAYER_PID 2>/dev/null

echo "=================================="
echo "Test complete!"