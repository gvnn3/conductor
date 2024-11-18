package lib

import (
	"fmt"
	"net"
)

type Step interface {
	Run() RetVal
}

type RetVal struct {
	Code    int
	Message string
}

func (r RetVal) Send(conn net.Conn) {
	fmt.Fprintf(conn, "%d: %s\n", r.Code, r.Message)
}

const (
	RETVAL_DONE = iota
)

type Phase struct {
	ResultHost string
	ResultPort string
	Steps      []Step
	Results    []RetVal
}

func NewPhase(resulthost, resultport string) *Phase {
	return &Phase{
		ResultHost: resulthost,
		ResultPort: resultport,
		Steps:      []Step{},
		Results:    []RetVal{},
	}
}

func (p *Phase) Load() {
	// Load a set of Steps into the list to be run
}

func (p *Phase) Append(step Step) {
	p.Steps = append(p.Steps, step)
}

func (p *Phase) Run() {
	// Execute all the steps
	for _, step := range p.Steps {
		ret := step.Run()
		p.Results = append(p.Results, ret)
	}
}

func (p *Phase) ReturnResults() {
	// Return the results of the steps
	for _, result := range p.Results {
		conn, err := net.Dial("tcp", net.JoinHostPort(p.ResultHost, p.ResultPort))
		if err != nil {
			fmt.Println("Error connecting:", err)
			continue
		}
		result.Send(conn)
		conn.Close()
	}
	conn, err := net.Dial("tcp", net.JoinHostPort(p.ResultHost, p.ResultPort))
	if err != nil {
		fmt.Println("Error connecting:", err)
		return
	}
	ret := RetVal{Code: RETVAL_DONE, Message: "phases complete"}
	ret.Send(conn)
	conn.Close()
}
