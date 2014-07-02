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
# Description: The Player listens on a well known port and executes
# commands as they are passed in, returning the reults up the pipe.

import socket
import pickle
import pickletools

import step
import phase
import retval

class Player():

    done = False
    sock = None
    
    def __init__(self, command, results, key = None):
        self.cmdsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.cmdsock.bind(command)
        self.cmdsock.listen(5)
        self.ressock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.ressock.bind(results)
        self.ressock.listen(5)

    def run(self):
        while not self.done:
            sock,addr = self.cmdsock.accept()
            data = sock.recv(65536)
            message = pickle.loads(data)
            if type(message) == phase.Phase:
                message.run(sock)
            sock.close()


def __main__():

    play = Player(('127.0.0.1', 5555),('127.0.0.1', 5556))
    play.run()
    
if __name__ == "__main__":
    __main__()
