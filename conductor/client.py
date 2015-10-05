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

import configparser
import socket
import pickle
import struct

from conductor import phase
from conductor import step
from conductor import run
from conductor import retval

class Client():

    def __init__(self, config):
        """Load up all the config data, including all phases"""
        master = config['Master']
        self.conductor = master['conductor']
        self.player = master['player']
        self.cmdport = int(master['cmdport'])
        self.resultport = int(master['resultsport'])

        self.startup_phase = phase.Phase(self.conductor, self.resultport)
        for i in config['Startup']:
            self.startup_phase.append(step.Step(config['Startup'][i]))

        self.run_phase = phase.Phase(self.conductor, self.resultport)
        for i in config['Run']:
            if (i.find('spawn') != -1):
                self.run_phase.append(step.Step(config['Run'][i], spawn=True))
            elif (i.find('timeout') != -1):
                # Timeout value MUST follow the keyword
                self.run_phase.append(step.Step(config['Run'][i],
                                        timeout=int(i.replace('timeout',''))))
            else:
                self.run_phase.append(step.Step(config['Run'][i]))

        self.collect_phase = phase.Phase(self.conductor, self.resultport)
        for i in config['Collect']:
            self.collect_phase.append(step.Step(config['Collect'][i]))
        
        self.reset_phase = phase.Phase(self.conductor, self.resultport)
        for i in config['Reset']:
            self.reset_phase.append(step.Step(config['Reset'][i]))

    def download(self, current):
        """Send a phase down to the player"""
        try:
            cmd = socket.create_connection((self.player, self.cmdport))
        except:
            print("Failed to connect to: ", self.player, self.cmdport)
            exit()
        cmd.settimeout(1.0)
        splat = pickle.dumps(current,pickle.HIGHEST_PROTOCOL)
        cmd.sendall(splat)

        message = self.len_recv(cmd);

        if (len(message) > 0):
            ret = pickle.loads(message)
            print(ret.code, ret.message)
        cmd.close()
        
    def doit(self):
        """Tell the remote player to execute the current phase"""
        try:
            cmd = socket.create_connection((self.player, self.cmdport))
        except:
            print("Failed to connect to: ", self.player, self.cmdport)
            exit()
        cmd.settimeout(1.0)
        splat = pickle.dumps(run.Run(),pickle.HIGHEST_PROTOCOL)
        cmd.sendall(splat)
        cmd.close()
        # Setup the callback socket for the player now
        self.ressock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.ressock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.ressock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.ressock.bind(('0.0.0.0',self.resultport))
        self.ressock.listen(5)
        
    def results(self):
        """Retrieve all the results from the player for the current phase"""
        done = False
        while not done:
            sock,addr = self.ressock.accept()
            data = self.len_recv(sock)
            message = pickle.loads(data)
            if type(message) == retval.RetVal:
                if message.code == retval.RETVAL_DONE:
                    print ("done")
                    done = True
                else:
                    print (message.code, message.message)
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
        self.download(self.collect_phase)

    def len_recv(self, sock):
        """Get the length of the message we're about to receive"""
        buf = b''
        retbuf = b''
        
        while len(buf) < 4:
           buf += sock.recv(4 - len(buf))

        length = socket.ntohl(struct.unpack('!I', buf)[0])

        while len(retbuf) < length:
           retbuf += sock.recv(length - len(retbuf));

        return retbuf;

