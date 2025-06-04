# Conductor Configuration Examples

This directory contains example configurations for common testing scenarios.

## Available Examples

### 1. Web Load Test (`web_load_test.cfg`)
A comprehensive web application load test that coordinates:
- Web server monitoring
- Multiple load generators
- Performance monitoring

**Components:**
- `web_server.cfg` - The server under test
- `load_generator1.cfg` - First load generator
- `monitor.cfg` - Monitoring node

**Usage:**
```bash
# Start players on each machine
player web_server.cfg      # On web server
player load_generator1.cfg # On load gen 1
player monitor.cfg         # On monitor

# Run test from conductor
conduct web_load_test.cfg
```

### 2. Database Performance Test (`database_test.cfg`)
Tests database performance with multiple concurrent clients.

**Components:**
- `database_server.cfg` - Database server configuration
- `database_client1.cfg` - First database client
- `database_client2.cfg` - Second database client

**Features:**
- Connection pool testing
- Query performance monitoring
- Transaction throughput measurement

### 3. Network Latency Test (`network_test.cfg`)
Measures network latency and throughput between nodes.

**Use Cases:**
- Datacenter connectivity testing
- WAN link performance
- Network troubleshooting

### 4. Distributed System Test (`distributed_test.cfg`)
Tests a complete distributed system with multiple components.

**Includes:**
- Load balancer configuration
- Multiple application servers
- Database cluster
- Cache servers

## Configuration Tips

### Command Types

1. **Normal Commands** - Wait for completion
   ```ini
   step1 = echo "This runs and waits"
   ```

2. **Spawn Commands** - Run in background
   ```ini
   spawn1 = tail -f /var/log/app.log
   ```

3. **Timeout Commands** - Run with time limit
   ```ini
   timeout60 = stress --cpu 4 --timeout 60
   ```

### Best Practices

1. **Always include cleanup** in the Reset phase
2. **Create result directories** in Startup phase
3. **Use spawn for monitoring** commands
4. **Collect logs and metrics** in Collect phase
5. **Test locally first** with localhost configurations

### Common Patterns

#### Monitoring Pattern
```ini
[Run]
spawn1 = vmstat 1 > /tmp/vmstat.log
spawn2 = iostat -x 1 > /tmp/iostat.log
spawn3 = top -b -d 1 > /tmp/top.log
```

#### Health Check Pattern
```ini
[Run]
timeout5 = curl -f http://localhost/health || echo "Failed"
```

#### Result Collection Pattern
```ini
[Collect]
step1 = mkdir -p /tmp/results
step2 = cp /var/log/app.log /tmp/results/
step3 = tar -czf /tmp/results.tgz /tmp/results/
```

## Customizing Examples

To customize these examples for your environment:

1. **Update IP addresses** in the [Master] section
2. **Modify commands** for your specific applications
3. **Adjust timeouts** based on your test duration
4. **Add more steps** as needed

## Creating Your Own

To create a new test configuration:

1. Copy an example that's similar to your use case
2. Update the [Master] section with your network details
3. Modify the phases (Startup, Run, Collect, Reset)
4. Test with a single client first
5. Scale up to multiple clients

## Troubleshooting

If examples don't work:

1. **Check network connectivity** between conductor and players
2. **Verify ports 6970/6971** are open
3. **Ensure commands exist** on player machines
4. **Check file permissions** for output directories
5. **Review player output** for error messages

For more help, see the [Installation Guide](../INSTALLATION_GUIDE.md).