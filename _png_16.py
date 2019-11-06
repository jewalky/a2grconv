# -*- coding: utf-8 -*-

import sys
import glob
import re
import struct
import os
from PIL import Image
import sys

# conversion
def convert_inputs(inputs, output):
    with open(output, 'wb') as f:
        print('writing: %s' % output)
        inputnum = -1
        for input in inputs:
            inputnum+=1
            pil_img = Image.open(input, 'r').convert('RGBA')
            pil_w, pil_h = pil_img.size
            packed_pixels = bytearray()
            count_zero = 0
            data = list(pil_img.getdata())
            i = -1
            while i < len(data):
                i += 1
                pixel = data[i] if i < len(data) else None
                y = int(i / pil_w)
                x = i % pil_w
                if pixel is not None and pixel[3] <= 0x0F: # zero alpha
                    count_zero += 1
                else:
                    # write RLE for empty pixels
                    if count_zero > 0:
                        # if we have too many rows...
                        global_offset = i - count_zero
                        max_store = 0x3F
                        # check first end of line
                        x = global_offset % pil_w
                        if x+count_zero >= pil_w:
                            eol = pil_w - x
                            eol_left = eol
                            while eol_left > 0:
                                c = min(0x3F, eol_left)
                                packed_pixels += struct.pack('<B', 0x80|(c&0x3F))
                                eol_left -= c
                            global_offset += eol
                            count_zero -= eol
                        count_rows = int(count_zero / pil_w)
                        while count_rows > 0:
                            c = min(0x3F, count_rows)
                            packed_pixels += struct.pack('<B', 0x40|(c&0x3F))
                            count_rows -= c
                            global_offset += c
                        count_cols = int(count_zero % pil_w)
                        while count_cols > 0:
                            # count_cols cannot cross row boundary
                            c = min(0x3F, count_cols)
                            global_x = global_offset % pil_w
                            if global_x + c > pil_w:
                                c = pil_w - global_x
                            packed_pixels += struct.pack('<B', 0x80|(c&0x3F))
                            count_cols -= c
                            global_offset += c
                        count_zero = 0
                    if pixel is not None and pixel[3] > 0x0F:
                        # write non-empty pixels
                        # iterate until empty pixel is found
                        non_empty = []
                        offs = i-1
                        while offs < len(data)-1:
                            offs += 1
                            if data[offs][3] > 0x0F:
                                non_empty.append(data[offs][3])
                                i = offs
                            else:
                                i = offs-1
                                break
                        color_bytes = []
                        for j in range(len(non_empty)):
                            if j % 2 == 0: # even pixel
                                byte = int(non_empty[j] / 16) & 0x0F
                                if j+1 < len(non_empty):
                                    byte |= (int(non_empty[j+1] / 16) << 4) & 0xF0
                                color_bytes.append(byte)
                        while len(color_bytes):
                            bytes_slice = color_bytes[:0x3F]
                            color_bytes = color_bytes[0x3F:]
                            packed_pixels += struct.pack('<B', len(bytes_slice))
                            packed_pixels += bytearray(bytes_slice)
            f.write(struct.pack('<III', pil_w, pil_h, len(packed_pixels)))
            f.write(packed_pixels)
        f.write(struct.pack('<I', len(inputs)))
                
                
# command line parsing

filenames = []
argv_begin = 2 if __name__ != '__main__' else 1
for fn in sys.argv[argv_begin:]:
    filenames += glob.glob(fn)

# make all slashes forward, remove duplicate slashes
# this is so that I can use regular split() to find out filename
def normalize_name(fn):
    fn = re.sub(r"[\/\\]+", '/', fn)
    return fn
    
filenames = [fn for fn in filenames]
    
inputs = []
for fn in filenames:
    ft = fn.split('.')[-1].lower()
    print(fn, ft)
    if ft == '16': # convert inputs to this file
        convert_inputs(inputs, fn)
        inputs = []
    else:
        inputs.append(fn)

if inputs:
    convert_inputs(inputs, 'sprites.16')
