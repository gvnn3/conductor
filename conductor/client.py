# Copyright (c) 2014, Neville-Neil Consulting
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
#
# Neither the name of Neville-Neil Consulting nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# Author: George V. Neville-Neil
#
# Description: All the information for the clients controlled by the
# conductor.

import socket
import struct

from conductor import phase
from conductor import step
from conductor import retval
from conductor.json_protocol import (
    send_message,
    receive_message,
    MSG_PHASE,
    MSG_RUN,
    MSG_RESULT,
)


class Client:
    def __init__(self, config, max_message_size=10):
        """Load up all the config data, including all phases"""
        # Store the config for reference
        self.config = config
        self.max_message_size = max_message_size * 1024 * 1024  # Convert MB to bytes

        coordinator = config["Coordinator"]
        self.conductor = coordinator["conductor"]
        self.player = coordinator["player"]

        # Validate and convert ports
        try:
            self.cmdport = int(coordinator["cmdport"])
            if self.cmdport < 1 or self.cmdport > 65535:
                raise ValueError(
                    f"Command port must be between 1 and 65535, got {self.cmdport}"
                )
        except ValueError as e:
            raise ValueError(f"Invalid command port: {coordinator['cmdport']}") from e

        try:
            self.resultport = int(coordinator["resultsport"])
            if self.resultport < 1 or self.resultport > 65535:
                raise ValueError(
                    f"Results port must be between 1 and 65535, got {self.resultport}"
                )
        except ValueError as e:
            raise ValueError(
                f"Invalid results port: {coordinator['resultsport']}"
            ) from e

        self.startup_phase = phase.Phase(self.conductor, self.resultport)
        for i in config["Startup"]:
            cmd = config["Startup"][i]
            # Check if the key name indicates spawn behavior
            if i.startswith("spawn"):
                self.startup_phase.append(step.Step(cmd, spawn=True))
            else:
                self.startup_phase.append(step.Step(cmd))

        self.run_phase = phase.Phase(self.conductor, self.resultport)
        for i in config["Run"]:
            cmd = config["Run"][i]
            # Check if the key name indicates special behavior
            if i.startswith("spawn"):
                self.run_phase.append(step.Step(cmd, spawn=True))
            elif i.startswith("timeout"):
                # Extract timeout value from key name
                timeout_str = i.replace("timeout", "")
                if timeout_str.isdigit():
                    self.run_phase.append(
                        step.Step(cmd, timeout=int(timeout_str))
                    )
                else:
                    self.run_phase.append(step.Step(cmd))
            # Also check if the command itself starts with spawn: or timeout:
            elif cmd.startswith("spawn:"):
                self.run_phase.append(
                    step.Step(cmd.replace("spawn:", "", 1), spawn=True)
                )
            elif cmd.startswith("timeout"):
                # Extract timeout value and command
                parts = cmd.split(":", 1)
                if len(parts) == 2:
                    timeout_str = parts[0].replace("timeout", "")
                    if timeout_str.isdigit():
                        self.run_phase.append(
                            step.Step(parts[1], timeout=int(timeout_str))
                        )
                    else:
                        self.run_phase.append(step.Step(cmd))
                else:
                    self.run_phase.append(step.Step(cmd))
            else:
                self.run_phase.append(step.Step(cmd))

        self.collect_phase = phase.Phase(self.conductor, self.resultport)
        for i in config["Collect"]:
            self.collect_phase.append(step.Step(config["Collect"][i]))

        self.reset_phase = phase.Phase(self.conductor, self.resultport)
        for i in config["Reset"]:
            self.reset_phase.append(step.Step(config["Reset"][i]))


    def download(self, current):
        """Send a phase down to the player"""
        cmd = None
        try:
            cmd = socket.create_connection((self.player, self.cmdport))
            cmd.settimeout(1.0)

            # Convert phase to JSON-serializable format
            phase_data = {
                "resulthost": current.resulthost,
                "resultport": current.resultport,
                "steps": [
                    {"command": s.command, "spawn": s.spawn, "timeout": s.timeout}
                    for s in current.steps
                ],
            }

            send_message(cmd, MSG_PHASE, phase_data, max_message_size=self.max_message_size)

            # Receive response
            msg_type, data = receive_message(cmd, max_message_size=self.max_message_size)
            if msg_type == MSG_RESULT:
                print(data.get("code", 0), data.get("message", ""))
                
        except Exception as e:
            print(f"Failed to connect to {self.player}:{self.cmdport} - {e}")
            # Don't exit! Let the caller handle the error
        finally:
            if cmd:
                cmd.close()

    def doit(self):
        """Tell the remote player to execute the current phase"""
        cmd = None
        try:
            cmd = socket.create_connection((self.player, self.cmdport))
            cmd.settimeout(1.0)
            send_message(cmd, MSG_RUN, {}, max_message_size=self.max_message_size)
            
            # Setup the callback socket for the player now
            self.ressock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            self.ressock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # SO_REUSEPORT is not available on all platforms, use try/except
            try:
                self.ressock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except AttributeError:
                pass  # SO_REUSEPORT not available on this platform
            self.ressock.bind(("0.0.0.0", self.resultport))
            self.ressock.listen(5)
            
        except Exception as e:
            print(f"Failed to connect to {self.player}:{self.cmdport} - {e}")
            # Don't exit! Let the caller handle the error
        finally:
            if cmd:
                cmd.close()

    def results(self, reporter=None):
        """Retrieve all the results from the player for the current phase"""
        done = False
        while not done:
            sock, addr = self.ressock.accept()
            msg_type, data = receive_message(sock, max_message_size=self.max_message_size)
            if msg_type == MSG_RESULT:
                code = data.get("code", 0)
                message = data.get("message", "")

                # Report the result
                if reporter:
                    reporter.add_result(code, message)
                else:
                    # Fallback to traditional printing
                    if code == retval.RETVAL_DONE:
                        print("done")
                    else:
                        print(code, message)

                if code == retval.RETVAL_DONE:
                    done = True
            sock.close()
        self.ressock.close()

    def startup(self):
        """Push the startup phase to the player"""
        self.download(self.startup_phase)

    def run(self):
        """Push the run phase to the player"""
        self.download(self.run_phase)

    def collect(self):
        """Push the collection phase to the player"""
        self.download(self.collect_phase)

    def reset(self):
        """Push the rset phase to the player"""
        self.download(self.reset_phase)

