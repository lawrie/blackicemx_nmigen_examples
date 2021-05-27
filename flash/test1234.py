import sys

with open(sys.argv[1], "wb") as f:
    for i in range(32768):
        f.write((i & 0xFF).to_bytes(1, byteorder='big'))

