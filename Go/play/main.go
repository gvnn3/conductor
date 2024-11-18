package main

import (
	"bytes"
	"encoding/gob"
	"fmt"
	"net"
)

type Player struct {
	Host string
	Port string
}

func NewPlayer(host, port string) *Player {
	return &Player{
		Host: host,
		Port: port,
	}
}

func (p *Player) sendResult(result map[string]string) error {
	conn, err := net.Dial("tcp", net.JoinHostPort(p.Host, p.Port))
	if err != nil {
		return fmt.Errorf("error connecting: %v", err)
	}
	defer conn.Close()

	var buf bytes.Buffer
	enc := gob.NewEncoder(&buf)
	err = enc.Encode(result)
	if err != nil {
		return fmt.Errorf("error encoding result: %v", err)
	}

	_, err = conn.Write(buf.Bytes())
	if err != nil {
		return fmt.Errorf("error sending result: %v", err)
	}

	return nil
}

func (p *Player) Run() {
	// Implement the logic to run the player
	result := map[string]string{"status": "success", "message": "Player ran successfully"}
	err := p.sendResult(result)
	if err != nil {
		fmt.Printf("Error sending result: %v\n", err)
	}
}

func main() {
	player := NewPlayer("localhost", "8080")
	player.Run()
}
