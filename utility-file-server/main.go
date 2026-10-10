package main

import (
	"flag"
	"fmt"
	"log"
	"net"
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

func lanURLs(port int) []string {
	addrs, err := net.InterfaceAddrs()
	if err != nil {
		return nil
	}
	var urls []string
	for _, a := range addrs {
		ipnet, ok := a.(*net.IPNet)
		if !ok || ipnet.IP.IsLoopback() || ipnet.IP.To4() == nil {
			continue
		}
		urls = append(urls, fmt.Sprintf("http://%s:%d/", ipnet.IP, port))
	}
	return urls
}

func main() {
	lan := flag.Bool("lan", false, "listen on all network interfaces so other devices can connect")
	flag.Usage = func() {
		fmt.Fprintf(flag.CommandLine.Output(), "Usage: %s [-lan] [port]\n", flag.CommandLine.Name())
		fmt.Fprintf(flag.CommandLine.Output(), "Serve the current directory over HTTP (default port %d).\n", defaultPort)
		flag.PrintDefaults()
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

	addr := fmt.Sprintf("127.0.0.1:%d", port)
	if *lan {
		addr = fmt.Sprintf(":%d", port)
		fmt.Printf("Serving %s to your network at:\n", dir)
		for _, u := range lanURLs(port) {
			fmt.Printf("  %s\n", u)
		}
	} else {
		fmt.Printf("Serving %s on http://127.0.0.1:%d/ ...\n", dir, port)
	}
	log.Fatal(http.ListenAndServe(addr, logRequests(http.FileServer(http.Dir(dir)))))
}
