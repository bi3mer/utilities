CC      ?= cc
CFLAGS  ?= -std=c11 -Wall -Wextra -O2
NAME    := $(notdir $(CURDIR))
SRC     := src/main.c

.PHONY: all clean

all: build/$(NAME)

build/$(NAME): $(SRC) | build
	$(CC) $(CFLAGS) -o $@ $<

build:
	mkdir -p build

clean:
	rm -rf build