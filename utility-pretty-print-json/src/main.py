#!/usr/bin/env python3
import argparse
import json

def main():
    parser = argparse.ArgumentParser(description="Pretty Print JSON")
    parser.add_argument('file', type=str, help="JSON file to pretty print.")
    parser.add_argument('--indent', type=int, default=2, help='Number of spaces in pretty print.')
    args = parser.parse_args()

    with open(args.file, 'r') as f:
        j = json.load(f)
        print(json.dumps(j, indent=args.indent))

if __name__ == "__main__":
    main()