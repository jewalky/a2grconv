# -*- coding: utf-8 -*-

import sys
import glob
import re
import struct
import os
from PIL import Image
import sys

# conversion
def convert_inputs(inputs, output, palette):
    with open(output, 'wb') as f:
        print('writing: %s'%output)
        inputnum = -1
        # load all inputs
        in_data = []
        unique_colors = []
        pal = [0] * 256
        for input in inputs:
            inputnum+=1
            pil_img = Image.open(input, 'r').convert('RGBA')
            pil_w, pil_h = pil_img.size
            data = list(pil_img.getdata())
            for i in range(len(data)):
                opixel = data[i]
                pixel = (opixel[0] << 16) | (opixel[1] << 8) | (opixel[2])
                if pixel not in unique_colors:
                    unique_colors.append(pixel)
                pixel |= opixel[3] << 24
                data[i] = pixel
            d = {'w': pil_w, 'h': pil_h, 'data': data}
            in_data.append(d)
        print('unique colors: %d'%len(unique_colors))
        colormap = {}
        if len(unique_colors) > 256:
            # optimize colors using PIL
            # generate an image that has the same colors
            print('images have more than 256 colors in total, reducing...')
            # max row width = 1024
            tmp_w = min(1024, len(unique_colors))
            tmp_h = int(len(unique_colors) / tmp_w)+1
            if len(unique_colors) % tmp_w == 0:
                tmp_h -= 1
            cdata = []
            for col in unique_colors:
                cdata.append( ((col & 0xFF0000) >> 16, (col & 0x00FF00) >> 8, (col & 0x0000FF), 0xFF) )
            # pad with empty pixels until the end
            cdata += [(0, 0, 0, 0)] * (tmp_w*tmp_h - len(cdata))
            tmp_img = Image.new('RGBA', (tmp_w, tmp_h))
            tmp_img.putdata(cdata)
            tmp_img = tmp_img.quantize(256)
            cnewdata = tmp_img.getdata()
            pal_raw = tmp_img.getpalette()
            pal = [0] * 256
            # PIL stores palette in a quite weird way: 256 R bytes, 256 G bytes, 256 B bytes
            for i in range(256):
                c_r = pal_raw[3*i]
                c_g = pal_raw[3*i+1]
                c_b = pal_raw[3*i+2]
                pal[i] = (c_r << 16) | (c_g << 8) | c_b
            for i in range(len(cnewdata)):
                index = cnewdata[i]
                color = unique_colors[i]
                colormap[color] = index
        else:
            # map each color to itself: we have enough space
            cnum = -1
            for col in unique_colors:
                cnum += 1
                colormap[col] = cnum
                pal[cnum] = col
        # write palette
        for i in range(256):
            f.write(struct.pack('>I', pal[i] << 8))
        for d in in_data:
            inputnum+=1
            pil_w = d['w']
            pil_h = d['h']
            data = d['data']
            packed_pixels = bytearray()
            count_zero = 0
            i = -1
            while i < len(data):
                i += 1
                pixel = data[i] if i < len(data) else None
                y = int(i / pil_w)
                x = i % pil_w
                if pixel is not None and pixel <= 0x7F000000: # zero alpha
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
                    if pixel is not None and pixel > 0x7F000000:
                        # write non-empty pixels
                        # iterate until empty pixel is found
                        non_empty = []
                        offs = i-1
                        while offs < len(data)-1:
                            offs += 1
                            # to-do: map "data" color to palette index. for now write 0
                            if data[offs] > 0x7F000000:
                                non_empty.append(colormap[data[offs]&0xFFFFFF])
                                i = offs
                            else:
                                i = offs-1
                                break
                        color_bytes = []
                        for j in range(len(non_empty)):
                            color_bytes.append(non_empty[j])
                        while len(color_bytes):
                            bytes_slice = color_bytes[:0x3F]
                            color_bytes = color_bytes[0x3F:]
                            packed_pixels += struct.pack('<B', len(bytes_slice))
                            packed_pixels += bytearray(bytes_slice)

            f.write(struct.pack('<III', pil_w, pil_h, len(packed_pixels)))
            f.write(packed_pixels)
        f.write(struct.pack('<I', len(inputs)|0x80000000)) # 0x80000000 flag means we have embedded palette
        # if palette is not None, we need to write an indexed .BMP for palette
        if palette is not None:
            pal_data = None
            if '@' in palette:
                palette = palette.split('@')
                pal_file_index = int(palette[-1])
                palette = '@'.join(palette[:-1])
                if pal_file_index > len(in_data):
                    print('warning: palette sprite index is larger than total count, will use default!')
                    pal_data = None
                else:
                    pal_data = in_data[pal_file_index]
            if pal_data is None:
                # find whatever image with the most color variation in it
                pal_colors = 0
                for d in in_data:
                    used_colors = []
                    data = d['data']
                    for pixel in data:
                        idx = colormap[pixel & 0xFFFFFF]
                        if idx not in used_colors:
                            used_colors.append(idx)
                    if len(used_colors) > pal_colors or pal_data is None:
                        pal_colors = len(used_colors)
                        pal_data = d
            if pal_data is None:
                print('warning: cannot write palette (no suitable sprite frames)')
            else:
                img_w = pal_data['w']
                img_h = pal_data['h']
                img_data = pal_data['data']
                img = Image.new('P', (img_w, img_h))
                # put palette in it
                img_pal = []
                for color in pal:
                    img_pal += [(color&0xFF0000)>>16, (color&0x00FF00)>>8, (color&0x0000FF)]
                img.putpalette(img_pal)
                convdata = []
                for pixel in img_data:
                    convdata.append(colormap[pixel&0xFFFFFF])
                img.putdata(convdata)
                img.save(palette, 'BMP')

                
# command line parsing

filenames = []
read_palette = False
palette = None
argv_begin = 2 if __name__ != '__main__' else 1
for fn in sys.argv[argv_begin:]:
    if fn == '-p':
        read_palette = True
        continue
    elif read_palette:
        palette = fn
        read_palette = False
        continue
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
    if ft == '16': # convert inputs to this file
        convert_inputs(inputs, fn, palette)
        inputs = []
    else:
        inputs.append(fn)

if inputs:
    convert_inputs(inputs, 'sprites.256', palette)
