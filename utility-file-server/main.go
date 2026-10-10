package main

import (
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
)

const defaultPort = 42069

func logRequests(h http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		log.Printf("%s %s %s", r.RemoteAddr, r.Method, r.URL.Path)
		h.ServeHTTP(w, r)
	})
}

func main() {
	flag.Usage = func() {
		fmt.Fprintf(flag.CommandLine.Output(), "Usage: %s [port]\n", flag.CommandLine.Name())
		fmt.Fprintf(flag.CommandLine.Output(), "Serve the current directory over HTTP (default port %d).\n", defaultPort)
	}
	flag.Parse()

	port := defaultPort
	switch flag.NArg() {
	case 0:
	case 1:
		p, err := strconv.Atoi(flag.Arg(0))
		if err != nil || p < 1 || p > 65535 {
			fmt.Fprintf(os.Stderr, "Error: invalid port '%s'\n", flag.Arg(0))
			os.Exit(1)
		}
		port = p
	default:
		flag.Usage()
		os.Exit(1)
	}

	dir, err := os.Getwd()
	if err != nil {
		log.Fatal(err)
	}

	addr := fmt.Sprintf(":%d", port)
	fmt.Printf("Serving %s on http://0.0.0.0:%d/ ...\n", dir, port)
	log.Fatal(http.ListenAndServe(addr, logRequests(http.FileServer(http.Dir(dir)))))
}
