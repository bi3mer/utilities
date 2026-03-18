#include <getopt.h>
#include <stdio.h>
#include <stdlib.h>

static void usage(const char *prog) {
  fprintf(stderr, "Usage: %s [options]\n", prog);
  fprintf(stderr, "  -h  Show this help\n");
}

int main(int argc, char *argv[]) {
  int opt;
  while ((opt = getopt(argc, argv, "h")) != -1) {
    switch (opt) {
    case 'h':
      usage(argv[0]);
      return 0;
    default:
      usage(argv[0]);
      return 1;
    }
  }

  /* TODO: implement */
  return 0;
}