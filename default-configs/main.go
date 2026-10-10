package main

import (
	"flag"
	"fmt"
)

func main() {
	flag.Usage = func() {
		fmt.Fprintf(flag.CommandLine.Output(), "Usage: %s [options]\n", flag.CommandLine.Name())
		flag.PrintDefaults()
	}
	// TODO: add flags
	flag.Parse()

	fmt.Println("Empty project...")
}
