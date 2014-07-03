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
import retval
import run

def __main__():

    phases = []
    local_config = configparser.ConfigParser()
    local_config.read(sys.argv[1]) # Cheap and sleazy for now

    defaults = local_config['Master']
    host = defaults['host']
    cmdport = int(defaults['cmdport'])
    resport = int(defaults['resultsport'])

    ressock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    ressock.bind((host,resport))
    ressock.listen(5)

    startup = phase.Phase(host, resport)
    for i in local_config['Startup']:
        startup.append(step.Step(local_config['Startup'][i]))
    phases.append(startup)

    run_phase = phase.Phase(host, resport)
    for i in local_config['Run']:
        run_phase.append(step.Step(local_config['Run'][i]))
    phases.append(run_phase)

    collect = phase.Phase(host, resport)
    for i in local_config['Collect']:
        collect.append(step.Step(local_config['Collect'][i]))
    phases.append(collect)

    reset = phase.Phase(host, resport)
    for i in local_config['Reset']:
        reset.append(step.Step(local_config['Reset'][i]))
    phases.append(reset)

    for trial in range(int(defaults['trials'])):
        # Send our phases down
        for nextphase in phases:
            cmd = socket.create_connection((host, cmdport))
            cmd.settimeout(1.0)
            splat = pickle.dumps(nextphase,pickle.HIGHEST_PROTOCOL)
            cmd.sendall(splat)
            message = cmd.recv(65536)
            if (len(message) > 0):
                ret = pickle.loads(message)
                print(ret.code, ret.message)
            cmd.close()
            # Run our phase
            cmd = socket.create_connection((host, cmdport))
            cmd.settimeout(1.0)
            splat = pickle.dumps(run.Run(),pickle.HIGHEST_PROTOCOL)
            cmd.sendall(splat)
            cmd.close()
            done = False
            # Collect results
            while not done:
                sock,addr = ressock.accept()
                data = sock.recv(65536)
                message = pickle.loads(data)
                if type(message) == retval.RetVal:
                    if message.code == retval.RETVAL_DONE:
                        print ("done")
                        done = True
                    else:
                        print (message.code, message.message)
                sock.close()

if __name__ == "__main__":
    __main__()
