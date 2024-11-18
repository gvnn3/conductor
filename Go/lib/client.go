package lib

import (
	"encoding/binary"
	"net"
)

type Client struct {
	StartupPhase Phase
	RunPhase     Phase
	CollectPhase Phase
	ResetPhase   Phase
}

func (c *Client) Download(phase Phase) {
	// Implement the download logic
}

func (c *Client) Startup() {
	// Push the startup phase to the player
	c.Download(c.StartupPhase)
}

func (c *Client) Run() {
	// Push the run phase to the player
	c.Download(c.RunPhase)
}

func (c *Client) Collect() {
	// Push the collection phase to the player
	c.Download(c.CollectPhase)
}

func (c *Client) Reset() {
	// Push the reset phase to the player
	c.Download(c.ResetPhase)
}

func (c *Client) LenRecv(conn net.Conn) ([]byte, error) {
	// Get the length of the message we're about to receive
	buf := make([]byte, 4)
	retbuf := []byte{}

	_, err := conn.Read(buf)
	if err != nil {
		return nil, err
	}

	length := binary.BigEndian.Uint32(buf)

	retbuf = make([]byte, length)
	_, err = conn.Read(retbuf)
	if err != nil {
		return nil, err
	}

	return retbuf, nil
}
