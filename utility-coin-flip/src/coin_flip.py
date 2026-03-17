#!/usr/bin/env python3
import argparse
import random
import time
import sys

parser = argparse.ArgumentParser(description="Simulate coin flips.")
parser.add_argument("numflips", type=int, help="Number of times to flip.")
args = parser.parse_args()

if args.numflips < 1:
    parser.error("numflips must be at least 1.")

# --- Animation ---
COIN_FRAMES = [
    [
        "  ╭─────╮  ",
        "  │  H  │  ",
        "  ╰─────╯  ",
    ],
    [
        "  ╭─────╮  ",
        "  │ ))) │  ",
        "  ╰─────╯  ",
    ],
    [
        "   ╭───╮   ",
        "   │ | │   ",
        "   ╰───╯   ",
    ],
    [
        "    ╭─╮    ",
        "    │|│    ",
        "    ╰─╯    ",
    ],
    [
        "     |     ",
        "     |     ",
        "     |     ",
    ],
    [
        "    ╭─╮    ",
        "    │|│    ",
        "    ╰─╯    ",
    ],
    [
        "   ╭───╮   ",
        "   │ | │   ",
        "   ╰───╯   ",
    ],
    [
        "  ╭─────╮  ",
        "  │ ((( │  ",
        "  ╰─────╯  ",
    ],
    [
        "  ╭─────╮  ",
        "  │  T  │  ",
        "  ╰─────╯  ",
    ],
]

def animate_flip():
    cycles = 2
    for _ in range(cycles):
        for frame in COIN_FRAMES:
            sys.stdout.write("\033[3A")  # move up 3 lines
            for line in frame:
                sys.stdout.write(f"\r{line}\n")
            sys.stdout.flush()
            time.sleep(0.07)

    time.sleep(0.15)

    # Clear the coin
    sys.stdout.write("\033[3A")
    for _ in range(3):
        sys.stdout.write("\033[2K\n")  # erase line

    sys.stdout.write("\033[3A")        # return cursor to top of cleared area
    sys.stdout.flush()

def main():
    # Print blank lines so the cursor-up trick has room
    sys.stdout.write("\n\n\n")
    sys.stdout.flush()
    animate_flip()

    # --- Flip ---

    flips = [random.choice(("H", "T")) for _ in range(args.numflips)]
    heads = flips.count("H")
    tails = flips.count("T")

    print(f"  Heads : {heads} ({heads / args.numflips * 100:.1f}%)")
    print(f"  Tails : {tails} ({tails / args.numflips * 100:.1f}%)")

if __name__ == "__main__":
    main()
