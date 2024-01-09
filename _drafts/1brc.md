---
layout: post
title:  "Using MaPLe to Solve the One Billion Row Challenge"
mathjax: true
---

The [One Billion Row Challenge](https://www.morling.dev/blog/one-billion-row-challenge/)
took off recently, and I thought it would be fun to try solving it using
[MaPLe](https://github.com/MPLLang/mpl), or MPL for short. MPL is a compiler
for a parallel functional language with excellent scalability on multicore
machines. I have access to a 72-core (144 hyperthreaded) multicore server, so
let's see how fast we can get on that machine.

My code is
available [here](https://github.com/shwestrick/mpl-1brc).
To get good performance, I ended up implementing four key optimizations,
yielding a total of 10x improvement over my initial code.
Currently, I'm getting just about **2.3 seconds** to parse and process one billion
measurements on 72 cores. And, it could probably be even faster. (I'm using no fancy
parsing tricks, no SIMD, and fairly basic hashing.)

<img id="time-breakdown" width="80%" src="/assets/1brc/time-breakdown.svg">



## Algorithm

At a high-level, the parallel algorithm I implemented is pretty straightforward.
The idea is to accumulate temperature measurements in a hash table, using the
station names as keys. We can use a concurrent hash table to allow for
insertions and updates to proceed in parallel. For each station, we need to
compute the min, max, and average temperatures; these can be computed as
follows.
  1. Allocate a hash table $$T$$, with strings (station names) as keys, and tuples
$$(\ell, h, t, c)$$ as values. The tuple is used to store four components for each station:
        * $$\ell$$: the lowest (min) temperature recorded
        * $$h$$: the highest (max) temperature recorded
        * $$t$$: the total (sum) of all temperatures recorded
        * $$c$$: the count of the number of recorded temperatures
  2. In parallel, for each entry `<s>;<m>` in the input file (station name $$s$$, and measurement $$m$$), do the
  following **atomically**:
        * If $$s$$ is not yet in $$T$$, then insert: $$T[s] := (m, m, m, 1)$$
        * Otherwise, read the current value $$(\ell, h, t, c) = T[s]$$,
        and update with $$T[s] := (\min(m,\ell), \max(m,h), m+t, c+1)$$.
  3. After all insertions have completed, for each final entry $$s \mapsto (\ell, h, t, c)$$
  compute the average temperature: $$t/c$$.
  4. Output all results in sorted order in the appropriate format.


## Implementation and optimizations

To implement this in practice, and get good performance, plenty of optimizations
are needed. I ended up implementing four key optimizations, which brought
the 

