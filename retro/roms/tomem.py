import sys

with open(sys.argv[1], "rb") as f:
    byte = f.read(1)
    while byte != b"":
        print("".join("%02x" % (byte[0])))
        byte = f.read(1)
