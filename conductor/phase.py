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
# Description: A Phase object encapsulates a set of Steps to be taken
# by the Client when asked by the Conductor.

import socket

from conductor import retval


class Phase:
    """Each Phase contains one, or more, steps."""

    def __init__(self, resulthost, resultport):
        self.resulthost = resulthost
        self.resultport = resultport
        self.steps = []
        self.results = []

    def load(self):
        """Load a set of Steps into the list to be run"""
        pass

    def append(self, step):
        self.steps.append(step)

    def run(self):
        """Execute all the steps"""
        for step in self.steps:
            ret = step.run()
            self.results.append(ret)

    def return_results(self):
        """Return the results of the steps"""
        for result in self.results:
            ressock = socket.create_connection((self.resulthost, self.resultport))
            result.send(ressock)
            ressock.close()
        ressock = socket.create_connection((self.resulthost, self.resultport))
        ret = retval.RetVal(retval.RETVAL_DONE, "phases complete")
        ret.send(ressock)
        ressock.close()
