# Conductor - A system for testing distributed systems across a network #

Many test frameworks exist to test code on a single host or, across a
network, on a single server.  Conductor is a distributed system test
framework, written in Python, that can be used to coordinate a set of
tests among a set of clients.  The Conductor system allows a single
machine to control several systems, orchestrating tests that require
the cooperation of several networked devices.

Conductor is written in Python 3 and requires ONLY the

`py33-setuptools33 package.`

## Documentation ##

- **[Quick Start Guide](QUICK_START.md)** - Get running in 5 minutes
- **[Installation Guide](INSTALLATION_GUIDE.md)** - Detailed setup instructions
- **[Example Configurations](examples/)** - Real-world test examples
- **[Architecture Overview](ARCHITECTURE.md)** - System internals

## Installation ##

(Installing packages normally requires root privileges)

`sudo python3 setup.py install`

For detailed installation instructions, see the [Installation Guide](INSTALLATION_GUIDE.md).

## Usage ##

Conductor installs two scripts, player and conduct, which are used to
run and control tests on the systems involved.  Every test has a
master configuration file, usually named test.cfg, as well as a configuration
file for each host involved in the test.  Two simple test cases are
found in the tests/localhost and tests/timeout sub-directories.

```
tests/localhost/test.cfg    <- used by conduct script
tests/localhost/dut.cfg     <- used by player script
```

To familiarize yourself with the system let's try the localhost
test.  The localhost test requires only one system, rather than
a distributed set.  Open two terminal windows on the host.
In terminal 1 type:

`> player dut.cfg`

In terminal 2 type:

`> conduct test.cfg`

You *MUST* always start all players before the conductor.

The output of the conductor should look like this:

```
0 phase received
running
0 b'startup\n'
done
0 phase received
running
0 b'running\n'
0 b'PING 127.0.0.1 (127.0.0.1): 56 data bytes\n64 bytes from 127.0.0.1: icmp_seq=0 ttl=64 time=0.046 ms\n64 bytes from 127.0.0.1: icmp_seq=1 ttl=64 time=0.162 ms\n64 bytes from 127.0.0.1: icmp_seq=2 ttl=64 time=0.143 ms\n\n--- 127.0.0.1 ping statistics ---\n3 packets transmitted, 3 packets received, 0.0% packet loss\nround-trip min/avg/max/stddev = 0.046/0.117/0.162/0.051 ms\n'
done
0 phase received
running
0 b'collecting\n'
done
0 phase received
running
0 b'collecting\n'
done
```

Once the test is complete the conduct script will exit and return the
caller back to the shell prompt.  The player will continue to await
commands from another run of the conduct script.

## Commentary ##

A common use for Conductor is to test network devices, such as a
router or firewall, that are connected to multiple senders and
receivers.  Each of the senders, receivers, and the device under test
(DUT) are a *Player*, and another system is designated as the *Conductor*.

The players, read commands over a network channel, execute them and
return results to the conductor.

The conductor reads test descriptions from a configuration file,
written using Python's config parser, and executes the tests on the
players.

The tests are executed in *Phases*.  A *Phase* contains a set of internal
or external (shell/program) commands that are executed in order, per
client.  The four Phases currently defined are:

  * Startup

The *Startup* phase is where commands that are required to set up each
device are execute.  Examples include setting up network interfaces,
routing tables, as well as creating directories to hold result files
on the players.

  * Run

The *Run* phase contains the commands that are the core of the test.  An
example might be starting a number of transmitting and receiving
programs to generate and sink traffic through the DUT.

  * Collect

In the *Collect* phase the Conductor sends commands to the Players to
retrieve any data that was generated during the test, and places that
data into a results directory on the Conductor, for later analysis.

  * Reset

The last phase is the *Reset* phase, where the Conductor instructs the
Players to reset any configuration that might have been set in the
Startup phase and which might influence later test runs.  It is the
goal when writing Conductor tests that all the systems used in the
test return to the state they were in prior to the Startup phase.

Each Phase has three parts.  The Conductor first downloads the Phase
to the Player, but does not tell it to execute.  Downloading the Phase
to each client allows the Conductor to start each Phase nearly
simultaneously, although the fact that the Conductor itself serializes
its communication among the clients means that there is a small amount
of skew in when each Player is told to execute its steps.  

Each phase is made up of several steps.  There are two, special,
keywords for steps executed in the Run phase.

A *spawn* keyword (spawn:echo 30) will spawn the command as a
sub-process and not wait for it to execute, nor collect the program's
return value.  The spawn keyword is best used to start several
programs simultaneously, such as multiple network streams when testing
a piece of networking equipment.

A *timeout* keyword (timeout10:sleep 30) will execute the command with
a timeout.  The timeout is the number directly after the keyword and
is expressed in seconds.  A command executed with a timeout will be
interrupted by its parent if it doesn't exit before the timeout
expires.  In the example above the sleep command will try to sleep for
30 seconds but then be interrupted after 10 seconds.  The timeout
keyword is useful for programs that want to run forever or which wait
for human input unnecessarily.

This work supported by: Rubicon Communications, LLC (Netgate)
