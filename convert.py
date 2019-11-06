# -*- coding: utf-8 -*-

import sys

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: %s <command> <input1> [<input2> ...]'%(sys.argv[0]))
        print('Commands:')
        print(' 16_png  - convert .16 file(s) to PNG')
        print(' png_16  - convert PNG file(s) to .16')
        print(' 256_png - convert .256 file(s) to PNG')
        print(' png_256 - convert PNG file(s) to .256')
        sys.exit(0)
        
    cmd = sys.argv[1].lower()
    if cmd == '16_png':
        import _16_png
    elif cmd == 'png_16':
        import _png_16
    elif cmd == '256_png':
        import _256_png
    elif cmd == 'png_256':
        import _png_256
