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
# Description: A step allows us to encapsulate a command and work with
# it, including recording the errors and the like that we might get
# back from it.

import subprocess
import shlex

from conductor import retval


class Step:
    def __init__(self, command, spawn=False, timeout=30):
        # Store the original command for shell execution
        self.command = command
        try:
            self.args = shlex.split(command)
        except ValueError:
            # Handle invalid shell syntax like unclosed quotes
            # Fall back to simple split
            self.args = command.split()
        self.spawn = spawn
        self.timeout = timeout

    def run(self):
        if self.spawn:
            # For spawn mode, use the original command with shell=True
            output = subprocess.Popen(self.command, shell=True)
            return retval.RetVal(0, "Spawned")
        else:
            try:
                # Use shell=True to enable full shell features
                # Use the original command string to preserve quoting
                output = subprocess.check_output(
                    self.command,
                    shell=True,
                    timeout=self.timeout,
                    universal_newlines=True,
                    errors="replace",
                )
            except subprocess.CalledProcessError as err:
                print(
                    "Code: ",
                    err.returncode,
                    "Command: ",
                    err.cmd,
                    "Output: ",
                    err.output,
                )
                ret = retval.RetVal(err.returncode, str(err.cmd))
            except subprocess.TimeoutExpired:
                print("Timeout on: ", self.command)
                ret = retval.RetVal(
                    retval.RETVAL_ERROR,
                    f"Command timed out after {self.timeout} seconds",
                )
            except FileNotFoundError:
                print("Command not found: ", self.args[0])
                ret = retval.RetVal(
                    retval.RETVAL_ERROR,
                    f"Command not found: {self.args[0]}",
                )
            else:
                print("Success: ", output)
                ret = retval.RetVal(0, output)
            return ret
