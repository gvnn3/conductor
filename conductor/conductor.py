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
# Description: Main program for conductor.  Reads the config, starts
# the players, parcels out the work, collects the results.

# "system" imports
import socket
import pickle
import configparser
import sys

# local imports
import phase
import step

def __main__():

    test = []
    config = configparser.ConfigParser()
    config.read(sys.argv[1]) # Cheap and sleazy for now

    defaults = config['Master']
    host = defaults['host']
    port = int(defaults['port'])

    startup = phase.Phase()

    for i in config['Startup']:
        startup.append(step.Step(config['Startup'][i]))

    test.append(startup)

    run = phase.Phase()
    
    for i in config['Run']:
        run.append(step.Step(config['Run'][i]))

    test.append(run)

    collect = phase.Phase()
        
    for i in config['Collect']:
        collect.append(step.Step(config['Collect'][i]))

    test.append(collect)

    reset = phase.Phase()
        
    for i in config['Reset']:
        reset.append(step.Step(config['Reset'][i]))

    test.append(reset)

    for trial in range(int(defaults['trials'])):
        for foo in test:
            sock = socket.create_connection((host, port))
            splat = pickle.dumps(foo,pickle.HIGHEST_PROTOCOL)
            sock.sendall(splat)
            sock.close()

if __name__ == "__main__":
    __main__()
