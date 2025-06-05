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
# Description: A return code object that can be pickled and sent back
# to the conductor.

from conductor.json_protocol import send_message, MSG_RESULT

RETVAL_OK = 0
RETVAL_ERROR = 1
RETVAL_BAD_CMD = 2
RETVAL_DONE = 65535


class RetVal:
    def __init__(self, code=0, message=""):
        self.code = code
        self.message = message

    def send(self, sock):
        """Send this RetVal as a JSON message."""
        # Ensure code and message are JSON-serializable
        try:
            # Try to convert code to int if possible
            code = int(self.code)
        except (ValueError, TypeError):
            # If not convertible, use string representation
            code = str(self.code)

        # Ensure message is a string
        try:
            message = str(self.message)
        except Exception:
            # Fallback for objects that can't be stringified
            message = repr(self.message)

        data = {"code": code, "message": message}

        try:
            send_message(sock, MSG_RESULT, data)
        except (ValueError, TypeError) as e:
            # Handle circular references or other serialization issues
            # Send a simplified error message instead
            fallback_data = {
                "code": RETVAL_ERROR,
                "message": f"Serialization error: {type(e).__name__}: {str(e)}",
            }
            send_message(sock, MSG_RESULT, fallback_data)
