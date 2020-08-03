---
layout: post
title:  "Incrementally Selecting a GIF Color Palette by Sampling"
mathjax: true
---

While
[implementing a seam-carver]({% post_url 2020-07-29-seam-carve %}),
I ended going down a rabbit hole to implement GIF file support
for [`mpl`](https://github.com/mpllang/mpl). I couldn't find any existing code
out in the wild, so I decided to do everything from scratch.
Ultimately, I just wanted a quick-and-dirty implementation for
the world's most popular quick-and-dirty image file format.

At a high level, the problem is extremely simple: I have a 2D array of
pixels, say in RGB format, and I want to output these pixels as a `.gif`. It's
easy to find
documentation online explaining the GIF file format (for example,
check out Matthew Flickinger's very helpful
[What's In a GIF](http://matthewflickinger.com/lab/whatsinagif/index.html)).
But there's still one piece of the puzzle missing:
**a single GIF image can use at most 256 colors**.

This at first appears to be a major limitation: a simple image like the
following contains 87568 distinct colors!

<img width="100%" src="/assets/seam-carve/pano.jpg">

To represent this image as a GIF, we need to choose a small color palette
and then remap each pixel to a color from the palette. This process is known
as [color quantization](https://en.wikipedia.org/wiki/Color_quantization),
and there are a million different algorithms we could implement:
[median cut](https://en.wikipedia.org/wiki/Median_cut),
[k-means clustering](https://en.wikipedia.org/wiki/K-means_clustering),
[octree clutering](https://en.wikipedia.org/wiki/Octree),
[spatial quantization](https://www.researchgate.net/publication/220502178_On_spatial_quantization_of_color_images), etc.
Many of these are fairly complex. GIFs aren't meant to be complex...
GIFs are quick-and-dirty, and I just wanted a quick-and-dirty
solution, something that I could code from scratch in a day or two.

The algorithm I came up with has some interesting properties:
  * The amount of time and space required to generate the palette is only
  dependent on the number of colors in the palette, not on the size of the
  image.
  * It is an
  [anytime algorithm](https://en.wikipedia.org/wiki/Anytime_algorithm),
  meaning that if you stop the algorithm at any time, you will still have a
  valid solution (albeit perhaps low-quality).
  * Every color in the palette is a color that appears somewhere in the
  source image.
  * The algorithm is remarkably simple.

## The Algorithm

Ultimately, to select a palette color for each pixel,
we'll just do something really simple: pick the "closest" color in the palette.
So, our goal here is to
choose a palette where the distances of each source color to its nearest
palette color are minimized.

Ideally, we want the palette to be "well-spaced": for an image that contains
lots of different colors, the palette should not contain multiple colors that
are too similar. But for images with lots of similar colors, the palette should
be more dense.

The algorithm is inherently incremental. We begin with an empty palette, and
then add colors one-by-one until the palette is full.

1. Let $$P$$ be the palette, initially empty.
2. Repeat until $$P$$ is full:
    1. Sample $$K$$ colors from the image.
    2. Compute, for each color in the sample, its minimum distance to a
    color already in $$P$$.
    3. Pick the color with maximum minimum distance and add it to $$P$$.

At each step, by adding the "furthest" color from the existing palette, we
guarantee that the palette is well-spaced.

To make this algorithm fast, we need a good way of querying the nearest color
in the palette. For this, I used spatial hashing, which should be significantly
faster than using (for example) a kd-tree or oct-tree, because the data set
is so small.
