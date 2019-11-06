# -*- coding: utf-8 -*-

import sys
import glob
import re
import struct
import os
from PIL import Image

def load_palette(fn):
    with open(fn, 'rb') as f:
        f.seek(0x36, os.SEEK_SET)
        pal = []
        for i in range(256):
            pal.append(struct.unpack('>I', f.read(4))[0] >> 8)
        return pal

# conversion
def convert_inputs(inputs, output, palette):
    images = []
    for input in inputs:
        # 
        with open(input, 'rb') as f:
            f.seek(-4, os.SEEK_END)
            count_images = struct.unpack('<I', f.read(4))[0]
            have_palette = count_images & 0x80000000
            if not have_palette and palette is None:
                print('error: %s does not have own palette and no custom palette is specified'%input)
                sys.exit(1)
            count_images &= 0x7FFFFFFF
            print('reading: %s (%d images)'%(input, count_images))
            f.seek(0, os.SEEK_SET)
            if palette is not None:
                print('using palette: %s'%palette)
                pal = load_palette(palette)
                if have_palette:
                    f.seek(256*4, os.SEEK_CUR)
            elif have_palette:
                print('using internal palette')
                pal = []
                for i in range(256):
                    pal.append(struct.unpack('>I', f.read(4))[0] >> 8)
            else:
                pal = [0] * 256
            for i in range(count_images):
                pixels = []
                img_w, img_h, img_data_size = struct.unpack('<III', f.read(12))
                if img_w > 512 or img_h > 512 or img_data_size > 1000000:
                    print('error: invalid sprite %d: width %d, height %d, data size %d'%(i, img_w, img_h, img_data_size))
                    sys.exit(1)
                data_size = img_data_size
                while data_size > 0:
                    ipx = struct.unpack('<B', f.read(1))[0]
                    ipx |= ipx << 8
                    ipx &= 0xC03F
                    data_size -= 1
                    
                    if ipx & 0xC000 > 0:
                        if ipx & 0xC000 == 0x4000:
                            ipx &= 0x3F
                            pixels += [0x00000000] * (img_w * ipx)
                        else:
                            ipx &= 0x3F
                            pixels += [0x00000000] * ipx
                    else:
                        ipx &= 0x3F
                        # read N bytes of color
                        for j in range(ipx):
                            byte = struct.unpack('<B', f.read(1))[0]
                            data_size -= 1
                            color = pal[byte]
                            pixels.append(0xFF000000 | color)

                images.append([img_w, img_h, pixels])

    for i in range(len(images)):
        print('writing: %s'%(output%i))
        image = images[i]
        pil_img = Image.new('RGBA', (image[0], image[1]))
        pil_img.putdata(image[2])
        pil_img.save(output%i)
                
# command line parsing

filenames = []
palette = None
read_palette = False
argv_begin = 2 if __name__ != '__main__' else 1
for fn in sys.argv[argv_begin:]:
    if fn == '-p':
        read_palette = True
        continue
    elif read_palette:
        palette = fn
        read_palette = False
        continue
    filenames += glob.glob(fn) or [fn]

# make all slashes forward, remove duplicate slashes
# this is so that I can use regular split() to find out filename
def normalize_name(fn):
    fn = re.sub(r"[\/\\]+", '/', fn)
    return fn
    
filenames = [fn for fn in filenames]
output = None
    
inputs = []
for fn in filenames:
    ft = fn.split('.')[-1].lower()
    if ft == 'png': # convert inputs to this template
        convert_inputs(inputs, fn, palette)
        inputs = []
        palette = None
    else:
        inputs.append(fn)

if inputs:
    for input in inputs:
        split_input = input.split('/')
        base_input = '.'.join(split_input[-1].split('.')[:-1])
        dir_input = '/'.join(split_input[:-1]) if len(split_input) > 1 else '.'
        output = '%s/%s-%%03d.png'%(dir_input, base_input)
        convert_inputs([input], output, palette)
