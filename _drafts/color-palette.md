---
layout: post
title:  "Incrementally Selecting a GIF Color Palette by Sampling"
---

When implementing GIF file support for
[`mpl`](https://github.com/mpllang/mpl), I came across an interesting
problem. GIFs permit you to use at most 256 colors. So how do you select a
"good" color palette for an image?

This is essentially an image compression problem, and of course, there are
a million different ways we could first compress the image before converting
to GIF. Many of these are fairly complex. GIFs aren't meant to be complex...
GIFs are quick-and-dirty, and I just wanted a quick-and-dirty
solution, something that I could code from scratch in a day or two. Here's
what I came up with.

## Background: The GIF File Format

For more info, check out Matthew Flickinger's very helpful
[What's In a GIF](http://matthewflickinger.com/lab/whatsinagif/index.html).
This is a lifesaver.

At a high level, there are a few steps to encoding an image as a GIF.
  1. Select a color palette of at most 256 colors.
  2. Relabel every pixel with a palette index.
  3. Encode the stream of palette indices with a custom form of LZW
  compression.
  4. Dump these bytes into a file, together with some metadata.

## The Algorithm

Ultimately, to select
the color of each pixel in the compressed image, we'll just do something really
simple: pick the "closest" color in the palette. So, our goal here is to
choose a palette where the distances of each source color to its nearest
palette color are minimized.

Ideally, we want the palette to be "well-spaced": for an image that contains
lots of different colors, the palette should not contain multiple colors that
are too similar. But for images with lots of similar colors, the palette should
be more dense.

The algorithm is inherently incremental. We begin with an empty palette, and
then add colors one-by-one until the palette is full.

1. Let P be the palette, initially empty.
2. Repeat until P is full:
    1. Sample K colors from the image
    2. Compute, for each color in the sample, its minimum distance to a
    color already in P.
    3. Pick the color with maximum minimum distance and add it to P.

At each step, by adding the "furthest" color from the existing palette, we
guarantee that the palette is well-spaced.

To make this algorithm fast, we need a good way of querying the nearest color
in the palette. For this, I used spatial hashing, which should be significantly
faster than using (for example) a kd-tree or oct-tree, because the data set
is so small.

## Other approaches

In Charlie Tangora's [`gif-h`](https://github.com/charlietangora/gif-h) library,
the color palette is chosen by building a kd-tree and then averaging subtrees
near the leaves to "cap" the tree at the desired number of colors.

We could use an algorithm like K-means, where we choose 256 "buckets" of colors
and then move colors between buckets until the distances of all colors to
their bucket mean are (locally) minimized. I chose not to because it seemed
like overkill for such a simple task. But it's worth trying!
