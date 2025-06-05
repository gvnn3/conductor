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
# Description: A return code object that can be serialized and sent back
# to the conductor.

from conductor.json_protocol import send_message, MSG_RESULT

RETVAL_OK = 0
RETVAL_ERROR = 1
RETVAL_BAD_CMD = 2
RETVAL_DONE = 65535


class RetVal:
    def __init__(self, code=0, message=""):
        # Ensure code is an integer and message is a string
        # This matches actual usage throughout the codebase
        if not isinstance(code, int):
            raise TypeError(f"RetVal code must be an integer, got {type(code).__name__}")
        if not isinstance(message, str):
            raise TypeError(f"RetVal message must be a string, got {type(message).__name__}")
        
        self.code = code
        self.message = message

    def send(self, sock):
        """Send this RetVal as a JSON message."""
        # RetVal should always have integer code and string message
        # based on actual usage in the codebase
        data = {
            "code": self.code,
            "message": self.message
        }
        
        send_message(sock, MSG_RESULT, data)
