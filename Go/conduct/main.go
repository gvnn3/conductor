package main

import (
	"conduct/lib"
	"fmt"
	"os"

	"github.com/go-ini/ini"
)

func main() {
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
