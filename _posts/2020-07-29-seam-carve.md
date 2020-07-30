---
layout: post
title:  "Parallel Seam Carving"
date:   2020-07-29 12:13:00 -0400
---

[Seam carving](https://en.wikipedia.org/wiki/Seam_carving) is a technique
for *content-aware resizing*, which changes the size of an image while
attempting to preserve the interesting content of the image. The basic
idea behind the technique is to remove ***low-energy seams***: paths of pixels
that are similar to their surroundings. A removed seam can be either vertical or
horizontal, to reduce either the width or height of an image.

For example, here's a panorama I took a few years ago near Spruce Knob, WV.
The image is super wide, so let's carve it down:

<video width="700px" loop autoplay>
  <source src="/assets/carve.webm" type="video/webm" />
</video>

I recently implemented a seam-carver as a parallel benchmark for
[`mpl`](https://github.com/mpllang/mpl), so here are some details of that
process. Check out the `examples/src/seam-carve/` subdirectory in the `mpl`
repository to see the code.

## The Algorithm

The heart of the seam carving algorithm is a
[dynamic programming](https://en.wikipedia.org/wiki/Dynamic_programming)
equation that computes what we might call *minimum seam energies*.
For each row `i` and column `j`, let's define its ***minimum seam energy***
`M(i,j)` as the minimum energy of any partial seam that ends at row `i`,
column `j`, where the energy of a seam is just the cumulative
energy of its pixels. (Energy can be defined in many different ways, but a
simple approach that seems to work well is to use the image gradient.)

Writing `E(i,j)` for the energy of a pixel at row `i`, column `j`, we can
compute minimum seam energies with the following equation.

```
M(i,j) = E(i,j) + min( M(i-1,j-1), M(i-1,j), M(i-1,j+1) )
```

Once `M` has been fully computed, we can find the minimum overall seam by
working from bottom to top: first, we locate
the column `j` with smallest `M(h-1,j)` (where `h` is the height of the image);
next, we find which of the three pixels above it has minimum seam
energy; and then we find the minimum above that pixel, etc. When we reach
the top of the image, the path we took is the minimum overall seam.

To "carve" a seam, we just have to remove it from the image and then shift
the pixels to fill in the missing space. This can then be repeated as many
times as desired to remove lots of seams.

## Finding the minimum seam in parallel

# Row-major order (doesn't work)

The dependencies within the equation for `M` appear to offer a lot of
parallelism. The most obvious approach would be to use row-major order,
where each row is processed entirely in parallel before moving on to the
next row.

<img width="300px" src="/assets/seam-carve-equation.svg" />

However, there's a major problem in practice with this approach:
typical images are at most only a few thousand pixels wide! Within a single
row, there's just not enough work to parallelize without paying too much
for the parallelism itself.
In particular, I found that on my machine, a reasonable
[granularity](https://en.wikipedia.org/wiki/Granularity_%28parallel_computing%29)
is between 1000 and 2000 pixels. If we tried to use row-major order,
we wouldn't be able to extract *any* parallelism from typical images.
Even on high-definition images, say 4K resolution, we would have a maximum
possible speedup of 2x to 4x. Not good enough!

# Triangular-blocked strips

To extract more parallelism without reducing the grain size, we need a
better way to partition up the work. This is something that probably
*could* be done "automatically" (e.g. take a look at
[Rezaul Chowdhury](https://dblp.uni-trier.de/pers/c/Chowdhury:Rezaul_Alam.html)'s
work), but here we'll just try to design something ourselves.

What are all of the dependencies for a single value `M(i,j)`? Visually,
the dependencies form a triangle with the pointy-end pointing down:

<img width="400px" src="/assets/seam-carve-depend.svg" />

Now imagine splitting the image up into a bunch of ***strips***, where each
strip is a set of contiguous rows. One strip can be be processed in two rounds
of triangles, as depicted below, where we first do all of the downward-pointing
triangles in parallel, and then do all of the upward-pointing triangles.
This is only correct because the dependencies of each location are triangular
above it.

<img width="400px" src="/assets/seam-carve-strips.svg" />

(Note: We're using triangles of even width at the base, because these tile
naturally within a strip. If we wanted to use odd-width triangles, we would
still have to use even-width triangles to fill in the left-over space, so
we might as well make our lives easier and only use one type of triangle.)

Recall that a reasonable target granularity is about one or two thousand
pixels. If we use triangles with a base-width of 80, then each triangle
contains 1560 pixels. This is good news: an image of width 1K can fit
12 such triangles, yielding a maximum speedup of 12x. On a high-resolution
4K image, we can achieve up to 50x speedup.

## Implementation and performance

With [`mpl`](https://github.com/mpllang/mpl), I implemented the
triangular-blocking strategy. The code is available in the
`examples/src/seam-carve/` subdirectory.

Here are some performance numbers for
removing 10 seams from an image of size approximately 2600x600. The
row-major granularity is 1000 pixels, and the triangular granularity is
1560 pixels (base-width 80).

```
            P=1   P=10  P=20  P=30
row-major   0.66  0.38  0.38  0.38
triangular  0.78  0.18  0.12  0.11
```

On 1 processor (P = 1), the row-major strategy is faster by about 15%, but
quickly hits its maximum possible speedup of (for this input and grain size)
approximately 2x, seeing no additional improvement above 10 processors.
In contrast, the triangular strategy continues to get faster as the number
of processors increases, with self-speedups of about 4x on 10 processors and
7x on 20.

## Conclusion

Seam carving is a challenging benchmark for a number of reasons. It is
largely memory-bound, and the amount of parallelism for typical images
is fairly small... so small in fact, that the most obvious method for
parallelization (row-major order) extracts almost no parallelism. With a small
change, we were able to improve performance significantly: in particular,
the triangular strategy described here is 4x faster than the row-major strategy
on 30 processors, despite being 15% slower on a single core.

<!--
In code, we could do this in MPL as follows:

{% highlight sml %}
let
  val w = ... (* width *)
  val h = ... (* height *)
  fun E (i,j) = ... (* energy *)

  (* Store M as an array, where (i, j) is at index i*w+j.
   * Use setM to update values in the table, and M (which
   * gracefully handles out-of-bounds) for lookup. *)
  val arrayM = alloc (w * h)
  fun setM (i,j) x = Array.update (arrayM, i*w+j, x)
  fun M (i,j) =
    if i < 0 then
      0.0
    else if j < 0 orelse j > w then
      Real.posInf
    else
      Array.sub (arrayM, i*w+j)
in
  for (0,h) (fn i =>
    parfor (0,w) (fn j =>
      setM (i,j) ( E(i,j) + min(M(i-1,j-1), M(i-1,j), M(i-1,j+1)) )
    )
  )
end
{% endhighlight %}
-->
