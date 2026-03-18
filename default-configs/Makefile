CC      ?= cc
CFLAGS  ?= -std=c11 -Wall -Wextra -O2
NAME    := $(notdir $(CURDIR))
SRC     := src/main.c

.PHONY: all clean

all: bin/$(NAME)

bin/$(NAME): $(SRC) | bin
	$(CC) $(CFLAGS) -o $@ $

bin:
	mkdir -p bin

clean:
	rm -rf bin