import sys

with open(sys.argv[1], "wb") as f:
    for i in range(256):
        f.write(i.to_bytes(1, byteorder='big'))

