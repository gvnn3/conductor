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
import client

def __main__():

    test_config = configparser.ConfigParser()
    test_config.read(sys.argv[1]) # Cheap and sleazy for now

    defaults = test_config['Test']
    
    clients = []
    for i in test_config['Clients']:
        client_config = configparser.ConfigParser()
        client_config.read(test_config['Clients'][i]) 
        clients.append(client.Client(client_config))

    # In order to get things to run somewhat in parallel
    # we do the work in several phases.
    # 1. Download the specific phase
    # 2. Start all phases (doit() method)
    # 3. Collect results
    # These three steps are taken for each of the four phases.
    for trial in range(int(defaults['trials'])):
        for nextclient in clients:
            nextclient.startup()
        for nextclient in clients:
            nextclient.doit()
        for nextclient in clients:
            nextclient.results()
        for nextclient in clients:
            nextclient.run()
        for nextclient in clients:
            nextclient.doit()
        for nextclient in clients:
            nextclient.results()
        for nextclient in clients:
            nextclient.collect()
        for nextclient in clients:
            nextclient.doit()
        for nextclient in clients:
            nextclient.results()
        for nextclient in clients:
            nextclient.reset()
        for nextclient in clients:
            nextclient.doit()
        for nextclient in clients:
            nextclient.results()

if __name__ == "__main__":
    __main__()
