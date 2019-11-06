# a2grconv

This is a collection of scripts to convert ROM2 graphics (.16, .256) to and from PNG.

16A is currently not supported, may add it in the future.

spritesb.256 (transparency map) is not supported and there are plans to add it later.

## Prerequisites

1. Python 3.5+
2. `pip install pillow`


## Usage

### Convert files from .16 to PNG:

```
python convert.py 16_png sprites.16 [font1-%03d.png]
```

If output PNG name is not specified, it will default to input name and 3-digit index (e.g. sprites-000.png).

### Convert files from PNG to .16:

```
python convert.py png_16 font1*.png [font1.16]
```

If output sprite name is not specified, it will default to sprites.16.

### Convert files from .256 to PNG:

```
python convert.py 256_png sprites.256 [troll-%03d.png] [-p palette.pal]
```

If output PNG name is not specified, it will default to input name and 3-digit index (e.g. sprites-000.png).

If palette is not specified, the image will be converted with file's internal palette if present, or throw an error. If a palette is specified, the image will be converted with that palette.

Note: ROM2 palette is an indexed BMP, usually a snapshot of one of the sprite's frames.

### Convert files from PNG to .256:

```
python convert.py png_256 troll*.png [troll.256] [-p palette.pal[@spriteindex]]
```

If output sprite name is not specified, it will default to sprites.256.

You can optionally specify output palette name: in this case, a specified sprite index will be saved as indexed BMP to be used for ROM2 palette replacement. 
If output palette is specified, but not sprite index, it will try to use the most colorful sprite.

