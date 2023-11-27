---
layout: post
title:  "A Foray Into Futhark: Parallel Mergesort on the GPU"
mathjax: true
---

Futhark ([site](https://futhark-lang.org/),
[github](https://github.com/diku-dk/futhark))
is a functional programming language which compiles down to high-performance
GPU code. I highly recommend it for anyone interested in getting into GPU
programming. This post is about
my experience developing an efficient parallel mergesort in Futhark, which
is now available in the [diku-dk/sorts](https://github.com/diku-dk/sorts)
package. Source code [here](https://github.com/diku-dk/sorts/blob/ec85b0b86fd7b86886192ec9b33c70cf239b6870/lib/github.com/diku-dk/sorts/merge_sort.fut).