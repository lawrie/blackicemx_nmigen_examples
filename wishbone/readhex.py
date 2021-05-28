def readhex():
    f = open("progmem.hex","r")
    l = []
    while True:
        s = f.readline()
        if s:
            l.append(int(s,16))
        else:
            break
    f.close()
    return l

