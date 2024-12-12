package main

import (
	"ChubbyGo/BaseServer"
	_ "ChubbyGo/Config"
	"ChubbyGo/Connect"
	"os"

	"bytes"
	"encoding/gob"
	"fmt"
	"log"
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
	clientConfigs := Connect.CreateClient()
	err := clientConfigs.StartClient()
	if err != nil {
		log.Println(err.Error())
	}
	clientConfigs.SetUniqueFlake(uint64(os.Getpid())) // Use a random number for multiple tests

	filename := "/ls/ChubbyCell_Conductor/test.sh"
	// Open a directory and get a handle
	ok, fileFd := clientConfigs.Open(filename)
	if ok {
		fmt.Printf("Get fd success, instanceSeq is %d\n", fileFd.InstanceSeq)
	} else {
		fmt.Printf("Error!\n")
	}

	// Lock the newly created file
	ok, token := clientConfigs.Acquire(fileFd, BaseServer.ReadLock, 0)
	if ok {
		fmt.Printf("Acquire (%s) success, Token is %d\n", filename, token)
	} else {
		fmt.Printf("Acquire Error!\n")
	}

	// Delete the file with the token you locked yourself
	ok = clientConfigs.Release(fileFd, token)
	if ok {
		fmt.Printf("release (%s) success.\n", filename)
	} else {
		fmt.Printf("Release Error!\n")
	}

	player := NewPlayer("localhost", "8080")
	player.Run()
}
