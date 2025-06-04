# Conductor Quick Start Guide

Get up and running with Conductor in 5 minutes!

## 1. Installation (30 seconds)

```bash
# Clone and install
git clone https://github.com/benroeder/conductor.git
cd conductor
python3 -m venv venv
source venv/bin/activate
pip install setuptools configparser
python setup.py install
```

## 2. Localhost Demo (2 minutes)

### Create test configuration

**`demo.cfg`:**
```ini
[Test]
trials = 1

[Clients]
demo = demo_client.cfg
```

**`demo_client.cfg`:**
```ini
[Master]
player = 127.0.0.1
conductor = 127.0.0.1
cmdport = 6970
resultsport = 6971

[Startup]
step1 = echo "=== Starting Demo ==="
step2 = echo "Creating test directory..."
step3 = mkdir -p /tmp/conductor_demo

[Run]
step1 = echo "Running parallel commands..."
spawn1 = sleep 2 && echo "Background task complete" > /tmp/conductor_demo/background.txt
timeout5 = ping -c 10 google.com
step2 = ls -la /tmp/conductor_demo

[Collect]
step1 = echo "Collecting results..."
step2 = cat /tmp/conductor_demo/background.txt 2>/dev/null || echo "Background task still running"

[Reset]
step1 = echo "Cleaning up..."
step2 = rm -rf /tmp/conductor_demo
step3 = echo "=== Demo Complete ==="
```

### Run the demo

Terminal 1:
```bash
player demo_client.cfg
```

Terminal 2:
```bash
conduct demo.cfg
```

## 3. Real Network Example (2 minutes)

Testing between two machines:

### On Machine A (Conductor - 192.168.1.100)

**`network_test.cfg`:**
```ini
[Test]
trials = 1

[Clients]
machine_b = machine_b.cfg
```

**`machine_b.cfg`:**
```ini
[Master]
player = 192.168.1.101      # Machine B's IP
conductor = 192.168.1.100   # Machine A's IP
cmdport = 6970
resultsport = 6971

[Startup]
step1 = hostname
step2 = ifconfig | grep "inet "

[Run]
step1 = ping -c 5 192.168.1.100
step2 = netstat -an | grep ESTABLISHED

[Collect]
step1 = echo "Network test complete"

[Reset]
step1 = echo "Done"
```

### On Machine B (Player - 192.168.1.101)

```bash
player machine_b.cfg
```

### Back on Machine A

```bash
conduct network_test.cfg
```

## Common Use Cases

### 1. Web Server Load Test

```ini
[Run]
# Start monitoring
spawn1 = vmstat 1 > /tmp/vmstat.log
spawn2 = iostat -x 1 > /tmp/iostat.log

# Run load test
timeout300 = ab -n 100000 -c 50 http://localhost/

# Capture metrics
step1 = curl http://localhost/metrics
```

### 2. Database Performance Test

```ini
[Startup]
step1 = mysql -e "CREATE DATABASE IF NOT EXISTS testdb"
step2 = mysql testdb < /tmp/schema.sql

[Run]
# Multiple parallel queries
step1 = mysql testdb -e "SELECT COUNT(*) FROM users"
step2 = mysql testdb -e "SELECT * FROM orders WHERE date > NOW() - INTERVAL 1 DAY"
spawn1 = mysqlslap --auto-generate-sql --number-of-queries=1000

[Collect]
step1 = mysql -e "SHOW STATUS" > /tmp/mysql_status.txt
```

### 3. System Stress Test

```ini
[Run]
# CPU stress
timeout60 = stress --cpu 4

# Memory stress  
timeout60 = stress --vm 2 --vm-bytes 1G

# Disk I/O stress
spawn1 = dd if=/dev/zero of=/tmp/testfile bs=1M count=1000

# Monitor system
spawn2 = top -b -n 60 > /tmp/top.log
```

## Tips

1. **Use spawn for long-running tasks** that should run in background
2. **Use timeout for commands** that might hang or run too long
3. **Always test locally first** before distributed setup
4. **Check player is running** before starting conductor
5. **Keep configurations simple** and build complexity gradually

## Next Steps

- Read the full [Installation Guide](INSTALLATION_GUIDE.md)
- Check [example configurations](tests/) in the tests directory
- See [Architecture Documentation](ARCHITECTURE.md) for internals