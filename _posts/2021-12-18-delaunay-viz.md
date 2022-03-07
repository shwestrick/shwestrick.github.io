---
layout: post
title:  "Visualizations of Parallel Delaunay Triangulation"
mathjax: true
date:   2021-12-18 15:00:00 -0500
comments: true
---

In a
[Delaunay triangulation](https://en.wikipedia.org/wiki/Delaunay_triangulation),
no circumcircle contains another point.
Delaunay triangulations have a lot of applications: for example, in graphics,
to produce "nice" meshes which avoid skinny triangles.

<img width="400px" src="/assets/delaunay-viz/delaunay-not-delaunay.svg" />

Parallel algorithms for Delaunay triangulation are usually terribly complex.
More recently, a beautifully simple algorithm was presented at SPAA'16 in the
paper [Parallelism in Randomized Incremental Algorithms](https://dl.acm.org/doi/10.1145/2935764.2935766). We'll refer to this algorithm as **BGSS** for short,
named after its authors: Guy Blelloch, Yan Gu, Julian Shun, and Yihan Sun. In
this post, I'd like to give some intuition for how their algorithm works.

The BGSS algorithm is based on a classic incremental algorithm, commonly called
**rip-and-tent**. To insert a point, you "rip" out some triangles, and then
make a "tent" inside the resulting cavity.

For example below, we begin with a mesh and insert a new point. The set of
ripped triangles is highlighted in blue, and then tent of the new point is
drawn in red.

<table class="images">
<tr>
  <td><img src="/assets/delaunay-viz/rip-tent-single-0.jpg">before</td>
  <td><img src="/assets/delaunay-viz/rip-tent-single-1.jpg">rip-and-tent</td>
  <td><img src="/assets/delaunay-viz/rip-tent-single-2.jpg">after</td>
</tr>
</table>

<img width="50%" src="/assets/delaunay-viz/rip-tent-single.gif">

If we tried to insert multiple points simultaneously, the cavities created by
these points might overlap, and we wouldn't be able to build tents without
resolving conflicts somehow. The classic incremental algorithm is therefore
is entirely sequential: $$N$$ points are inserted one after another, taking
$$N$$ steps total.

However, when inserting multiple points simultaneously, **the cavities don't
always overlap**:

<table class="images">
<tr>
  <td><img src="/assets/delaunay-viz/rip-tent-double-0.jpg">before</td>
  <td><img src="/assets/delaunay-viz/rip-tent-double-1.jpg">rip-and-tent</td>
  <td><img src="/assets/delaunay-viz/rip-tent-double-2.jpg">after</td>
</tr>
</table>

<img width="50%" src="/assets/delaunay-viz/rip-tent-double.gif">

In their [paper](https://dl.acm.org/doi/10.1145/2935764.2935766),
Blelloch & friends showed something incredible: if you **randomly select a
batch** of points to insert simultaneously, then the number of overlapping
cavities will be small! More specifically, on a mesh of size $$M$$ and a sufficiently large (random)
batch, there should be about $$O(M)$$ points in the batch whose cavities do
not overlap.

Below are a couple examples. On the left, in a
mesh of size 1000, we see 61 points that can be inserted simultaneously. On
the right, 277 points simultaneously inserted into a mesh of size 5000.
These examples suggest that on a mesh of size $$M$$, we should expect to be
able to insert approximately $$M/20$$ random points simultaneously.

<table class="images">
<tr>
  <td><img src="/assets/delaunay-viz/batch-1000-61.png">61 insertions into mesh of size 1000</td>
  <td><img src="/assets/delaunay-viz/batch-5000-277.png">277 insertions into mesh of size  5000</td>
</tr>
</table>

Based on the above intuition, here's the gist of the BGSS algorithm:
1. Construct an initial mesh (e.g. a big bounding triangle).
2. Repeat until all points have been inserted:
  - Let $$M$$ be the size of the current mesh.
  - Randomly select a batch of $$O(M)$$ points to insert.
  - Pick a maximal subset of these points such that none of the cavities overlap.
  - In parallel, insert these points into the mesh by ripping and tenting.

For $$N$$ points overall, this algorithm takes $$O(N \log N)$$ work (in
expectation) and polylog span (w.h.p.). There are of course quite a few details
that I didn't cover here, like how to efficiently detect overlapping cavities
and select a "winner" in these cases. Perhaps I'll write another post about that
in the future. In the meantime, if you're curious, you could
peruse the [authors' code](https://github.com/cmuparlay/pbbsbench/tree/master/delaunayTriangulation/incrementalDelaunay).
If you're curious about performance details, check out this
[Twitter thread](https://twitter.com/shwestrick/status/1468296726016634892?s=20)
where I describe some of the challenges I encountered when optimizing an
implementation for [MPL](https://github.com/mpllang/mpl).

Finally, here's the algorithm running from an initial mesh of
size 1K up to a final size of 10K points. Enjoy!

<video width="85%" loop autoplay muted playsinline>
  <source src="/assets/delaunay-viz/animation.mp4" type="video/mp4" />
</video>
