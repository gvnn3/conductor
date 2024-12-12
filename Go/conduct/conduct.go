package main

import (
	"ChubbyGo/BaseServer"
	_ "ChubbyGo/Config"
	"ChubbyGo/Connect"
	"conduct/lib"
	"fmt"
	"log"
	"os"

	"github.com/go-ini/ini"
)

func main() {

	clientConfigs := Connect.CreateClient()
	err := clientConfigs.StartClient()
	if err != nil {
		log.Println(err.Error())
	}
	clientConfigs.SetUniqueFlake(uint64(os.Getpid())) // Use a random number for multiple tests
	// Open a directory and get a handle
	ok, fd := clientConfigs.Open("/ls/ChubbyCell_Conductor")
	if ok {
		fmt.Printf("Get fd success, instanceSeq is %d\n", fd.InstanceSeq)
	} else {
		fmt.Printf("Error!\n")
	}

	filename := "start.sh"
	// Create a file in the opened folder
	ok, fileFd := clientConfigs.Create(fd, BaseServer.PermanentFile, filename)
	if ok {
		fmt.Printf("Create file(%s) success, instanceSeq is %d, checksum is %d.\n", filename, fileFd.InstanceSeq, fileFd.ChuckSum)
	} else {
		fmt.Printf("Create Error!\n")
	}

	// Lock the newly created file
	ok, token := clientConfigs.Acquire(fileFd, BaseServer.ReadLock, 0)
	if ok {
		fmt.Printf("Acquire (%s) success, Token is %d\n", filename, token)
	} else {
		fmt.Printf("Acquire Error!\n")
	}

	ok = clientConfigs.Release(fileFd, token)
	if ok {
		fmt.Printf("release (%s) success.\n", filename)
	} else {
		fmt.Printf("Release Error!\n")
	}

	return

	if len(os.Args) < 2 {
		fmt.Println("Usage: conduct <config_file>")
		os.Exit(1)
	}

	configFile := os.Args[1]
	cfg, err := ini.Load(configFile)
	if err != nil {
		fmt.Printf("Fail to read file: %v\n", err)
		os.Exit(1)
	}

	// Example of reading values from the config file
	resultHost := cfg.Section("default").Key("result_host").String()
	resultPort := cfg.Section("default").Key("result_port").String()

	client := &lib.Client{
		StartupPhase: *lib.NewPhase(resultHost, resultPort),
		RunPhase:     *lib.NewPhase(resultHost, resultPort),
		CollectPhase: *lib.NewPhase(resultHost, resultPort),
		ResetPhase:   *lib.NewPhase(resultHost, resultPort),
	}

	client.Startup()
	client.Run()
	client.Collect()
	client.Reset()
}
