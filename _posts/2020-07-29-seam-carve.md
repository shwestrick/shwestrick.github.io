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

# Row-major order

The dependencies within the equation for `M` appear to offer a lot of
parallelism: if we proceed in row-major order, then each row can be
processed entirely in parallel.

<img width="300px" src="/assets/seam-carve-equation.svg" />

However, there's a major problem in practice with this approach:
typical images are at most only a few thousand pixels wide! This gives us
just a few thousand arithmetic instructions to parallelize at a time.
On modern multicore machines, this is simply
[too fine grained](https://en.wikipedia.org/wiki/Granularity_%28parallel_computing%29).

I found that on my machine, a reasonable granularity is 1000 pixels or more.
For an image of size 2000x2000 (4 million pixels), using row-major order,
we would be able to a maximum speedup of 2x. Not good enough.

# Triangular-blocked strips

To extract more parallelism without reducing the grain size, we need a
better way to partition up the work. This is something that probably
*could* be done "automatically" (e.g. take a look at
[Rezaul Chowdhury](https://dblp.uni-trier.de/pers/c/Chowdhury:Rezaul_Alam.html)'s
work), but here we'll just try to design something ourselves.

What are all of the dependencies for a single value `M(i,j)`? If we were
to visualize these, they would look like triangles with the pointy end pointing
down.

<img width="400px" src="/assets/seam-carve-depend.svg" />

Here I've shown two such dependency-triangles. This is just for illustration,
but it's worth pointing out that
we *could* do these two triangles in parallel if we wanted. There would be
a little bit of repeated work where they overlap, and the leftover space below
the triangles is not really a nice shape... but we *could*.

Let's look for a better arrangement of triangles: ideally, there should be
no overlap, and the leftover space should have a good shape.

Here's a nice
observation: if we use triangles with even-length base, then the leftover
space has the exact same shape, but upside down. So, we can complete a
*strip* (multiple rows) of the image by doing two sets of triangles in parallel.

<img width="400px" src="/assets/seam-carve-strips.svg" />


TODO:

* A bit more to write...
* the `.webm` above doesn't load on mobile???

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
