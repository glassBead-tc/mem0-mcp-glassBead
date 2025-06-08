#!/bin/bash

# mem0-mcp Manual Scaling Script
# Usage: ./scale.sh [start|stop|restart|status] [num_instances]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="$SCRIPT_DIR/pids"
LOG_DIR="$SCRIPT_DIR/logs"
BASE_PORT=8080
INSTANCES=${2:-4}  # Default to 4 instances

# Create directories
mkdir -p "$PID_DIR" "$LOG_DIR"

start_instance() {
    local port=$1
    local instance_num=$2
    
    echo "Starting mem0-mcp instance $instance_num on port $port..."
    
    python "$SCRIPT_DIR/main.py" --host 0.0.0.0 --port "$port" \
        > "$LOG_DIR/mem0-mcp-$instance_num.log" 2>&1 &
    
    local pid=$!
    echo $pid > "$PID_DIR/mem0-mcp-$instance_num.pid"
    
    echo "Started instance $instance_num (PID: $pid) on port $port"
}

stop_instance() {
    local instance_num=$1
    local pid_file="$PID_DIR/mem0-mcp-$instance_num.pid"
    
    if [[ -f "$pid_file" ]]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo "Stopping instance $instance_num (PID: $pid)..."
            kill "$pid"
            rm "$pid_file"
        else
            echo "Instance $instance_num not running (stale PID file)"
            rm "$pid_file"
        fi
    else
        echo "Instance $instance_num not running"
    fi
}

start_all() {
    echo "Starting $INSTANCES mem0-mcp instances..."
    for i in $(seq 0 $((INSTANCES - 1))); do
        local port=$((BASE_PORT + i))
        start_instance "$port" "$i"
        sleep 1  # Brief delay between starts
    done
    echo "All instances started. Ports: $BASE_PORT-$((BASE_PORT + INSTANCES - 1))"
}

stop_all() {
    echo "Stopping all mem0-mcp instances..."
    for pid_file in "$PID_DIR"/mem0-mcp-*.pid; do
        if [[ -f "$pid_file" ]]; then
            local instance_num=$(basename "$pid_file" .pid | sed 's/mem0-mcp-//')
            stop_instance "$instance_num"
        fi
    done
}

status() {
    echo "mem0-mcp Instance Status:"
    echo "========================"
    
    local running=0
    for pid_file in "$PID_DIR"/mem0-mcp-*.pid; do
        if [[ -f "$pid_file" ]]; then
            local instance_num=$(basename "$pid_file" .pid | sed 's/mem0-mcp-//')
            local pid=$(cat "$pid_file")
            local port=$((BASE_PORT + instance_num))
            
            if kill -0 "$pid" 2>/dev/null; then
                echo "Instance $instance_num: RUNNING (PID: $pid, Port: $port)"
                ((running++))
            else
                echo "Instance $instance_num: STOPPED (stale PID file)"
                rm "$pid_file"
            fi
        fi
    done
    
    echo "========================"
    echo "Running instances: $running"
}

case "$1" in
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
    restart)
        stop_all
        sleep 2
        start_all
        ;;
    status)
        status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status} [num_instances]"
        echo "  start    - Start specified number of instances (default: 4)"
        echo "  stop     - Stop all running instances"
        echo "  restart  - Stop and start all instances"
        echo "  status   - Show status of all instances"
        echo ""
        echo "Examples:"
        echo "  $0 start 6     # Start 6 instances on ports 8080-8085"
        echo "  $0 stop        # Stop all instances"
        echo "  $0 status      # Check instance status"
        exit 1
        ;;
esac 