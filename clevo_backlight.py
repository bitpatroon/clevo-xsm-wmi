#!/usr/bin/env python3
"""
Clevo X370SNx keyboard backlight — ITE 048d:8910 via USB HID.

Usage:
  clevo_backlight.py solid <R> <G> <B>        # alle toetsen één kleur (0-255)
  clevo_backlight.py color <naam>              # voorgedefinieerde kleur
  clevo_backlight.py off                       # backlight uit
  clevo_backlight.py brightness <0-255>        # alleen helderheid aanpassen

Optie:
  --dev /dev/hidrawN   HID device (default: /dev/hidraw4)

Geldige kleurmamen: red, green, blue, white, yellow, cyan, magenta, orange, purple
"""
import fcntl, sys, os

HIDRAW_DEFAULT = '/dev/hidraw4'
NUM_KEYS = 192   # indices 0-191 dekken alle fysieke toetsen

COLORS = {
    'red':     (255,   0,   0),
    'green':   (  0, 255,   0),
    'blue':    (  0,   0, 255),
    'white':   (255, 255, 255),
    'yellow':  (255, 255,   0),
    'cyan':    (  0, 255, 255),
    'magenta': (255,   0, 255),
    'orange':  (255, 165,   0),
    'purple':  (128,   0, 255),
    'off':     (  0,   0,   0),
}

def HIDIOCSFEATURE(n):
    return (3 << 30) | (n << 16) | (ord('H') << 8) | 6

def set_key(fd, idx, r, g, b):
    buf = (bytearray([0xCF, 0x01, idx, r, g, b]) + bytearray(65))[:65]
    fcntl.ioctl(fd, HIDIOCSFEATURE(65), buf)

def commit(fd, brightness=0xFF):
    buf = bytearray([0xCE, 0x01, brightness])
    fcntl.ioctl(fd, HIDIOCSFEATURE(3), buf)

def set_all(fd, r, g, b, brightness=0xFF):
    for i in range(NUM_KEYS):
        set_key(fd, i, r, g, b)
    commit(fd, brightness)

def main():
    args = sys.argv[1:]
    dev = HIDRAW_DEFAULT

    if '--dev' in args:
        i = args.index('--dev')
        dev = args[i + 1]
        args = args[:i] + args[i + 2:]

    if not args:
        print(__doc__)
        sys.exit(0)

    cmd = args[0]

    if not os.path.exists(dev):
        print(f"Fout: {dev} niet gevonden. Gebruik --dev om het juiste hidraw-apparaat op te geven.")
        sys.exit(1)

    with open(dev, 'rb+', buffering=0) as f:
        fd = f.fileno()

        if cmd == 'solid':
            if len(args) != 4:
                print("Gebruik: solid <R> <G> <B>")
                sys.exit(1)
            r, g, b = int(args[1]), int(args[2]), int(args[3])
            set_all(fd, r, g, b)

        elif cmd == 'color':
            if len(args) != 2 or args[1] not in COLORS:
                print(f"Onbekende kleur. Kies uit: {', '.join(COLORS)}")
                sys.exit(1)
            r, g, b = COLORS[args[1]]
            set_all(fd, r, g, b)

        elif cmd == 'off':
            set_all(fd, 0, 0, 0, brightness=0)

        elif cmd == 'brightness':
            if len(args) != 2:
                print("Gebruik: brightness <0-255>")
                sys.exit(1)
            level = int(args[1])
            commit(fd, level)

        else:
            print(f"Onbekend commando: {cmd}")
            print(__doc__)
            sys.exit(1)

if __name__ == '__main__':
    main()
