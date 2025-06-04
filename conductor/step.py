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

class Step():

    def __init__(self, command, spawn=False, timeout=30):
        self.args = shlex.split(command)
        self.spawn = spawn
        self.timeout = timeout
        
    def run(self):
        if self.spawn == True:
                output = subprocess.Popen(self.args)
                return retval.RetVal(0, "Spawned")
        else:
            try:
                output = subprocess.check_output(self.args,
                                                 timeout=self.timeout,
                                                 universal_newlines=True)
            except subprocess.CalledProcessError as err:
                print ("Code: ", err.returncode, "Command: ", err.cmd,
                       "Output: ", err.output)
                ret = retval.RetVal(err.returncode, err.cmd)
            except subprocess.TimeoutExpired as err:
                print ("Timeout on: ", self.args)
                ret = retval.RetVal(0, "Timeout")
            else:
                print ("Success: ", output)
                ret = retval.RetVal(0, output)
            return ret
            
    def ready(self):
        """Tell the server we're ready to go."""
        pass

    def wait_ready(self):
        """Wait on the server"""
        pass

    def wait(self, until):
        """Wait until time specified"""
        pass
