---
layout: post
title:  "Digital Reverb: Fast Comb Filters Are All You Need"
mathjax: true
comments: true
---

While browsing through
[The Computer Music Tutorial](https://mitpress.mit.edu/books/computer-music-tutorial)
by
[Curtis Roads](https://en.wikipedia.org/wiki/Curtis_Roads),
I came across a beautifully simple *reverberator* circuit. This circuit
simulates the acoustic effect of a particular space---such as a concert
hall or cathedral---using only two components:
[***comb***](https://en.wikipedia.org/wiki/Comb_filter) and
[***all-pass***](https://en.wikipedia.org/wiki/All-pass_filter) filters.
The filters can be tuned to simulate a variety of different spaces.

<img width="80%" src="/assets/reverb/design.svg">

<div class="remark">
This design is fairly old; it's credited to
[Manfred Schroeder](https://en.wikipedia.org/wiki/Manfred_R._Schroeder)
during his time at [Bell Labs](https://en.wikipedia.org/wiki/Bell_Labs)
in the mid 20<sup>th</sup> centure.
From what I can tell, nowadays people are mostly using alternative
techniques such as
[convolution reverb](https://en.wikipedia.org/wiki/Convolution_reverb).
</div>

My first thought was how fun it would be to turn this circuit
into a parallel benchmark for
[`mpl`](https://github.com/mpllang/mpl), the compiler I'm developing at
Carnegie Mellon University. And soon enough, I found myself deep in the rabbit
hole of writing code and running experiments.

Here are the results. Impressive, for a circuit so simple!

<table class="images">
<tr class="shrink ralign">
  <td>original</td>
  <td>
    <audio controls>
      <source src="/assets/reverb/priorities.mp3" type="audio/mp3">
      Your browser does not support audio playback.
    </audio>
  </td>
</tr>

<tr class="shrink ralign">
  <td>with reverb</td>
  <td>
    <audio controls>
      <source src="/assets/reverb/priorities-rev.mp3" type="audio/mp3">
      Your browser does not support audio playback.
    </audio>
  </td>
</tr>
</table>

**In this post, I describe the process of designing and implementing a fast
parallel reverb algorithm**, based on the circuit shown above.
At first, seeing as how the circuit is built
from two components (comb and all-pass filters), it might seem that we need to
design two algorithms.
But it turns out that if you have a fast algorithm for a
comb filter, then you essentially
[already have a fast all-pass algorithm](#all-pass-with-comb), for free. So most
of my effort went into
[designing and implementing a fast comb filter](#par-comb-section).

Feel free to [leave a note below](#respond) if you have any questions
or comments. If you're curious to see source code, check out
[my initial work](https://github.com/MPLLang/mpl/pull/122)
and
[recent improvements](https://github.com/MPLLang/mpl/commit/7fee9cdfce3fe56596ba93e25159b17aeef9e090)
(including the algorithm I describe below) on GitHub.

I hope you have as much fun reading through this as I did working on it!

## What is a Comb Filter?
{: #comb-filter}

A [feedback comb filter](https://en.wikipedia.org/wiki/Comb_filter#Feedback_form)
produces many equally-spaced echoes of a sound, where each echo is
dimished in intensity. I've drawn an example below. The input
appears first, colored in blue, and each distinct echo is a different color.
(The actual output signal would be the sum of all
these echoes together as one signal.)

<img src="/assets/reverb/comb-signal.svg">

Essentially, a comb filter combines two effects: attenuation and delay.

<table class="images">
<tr>
  <td><img src="/assets/reverb/attenuate.svg">Attenuation</td>
  <td><img src="/assets/reverb/delay.svg">Delay</td>
</tr>
</table>

If a large enough delay between echoes is used, the effect of a comb filter
is essentially the same as the looping "delay" effect which is sometimes
used by musicians (particularly electric guitarists, for example with
an
[effect pedal](https://en.wikipedia.org/wiki/Delay_(audio_effect)#Digital_delay)).
But when the delay is small---say, on the order
of milliseconds---the effect of a comb filter is primarily "spectral", causing
us to perceive it as modifying the
[quality of the sound](https://en.wikipedia.org/wiki/Timbre) itself.

<table class="images">
<tr class="shrink ralign">
  <td>original</td>
  <td>
    <audio controls>
      <source src="/assets/reverb/priorities.mp3" type="audio/mp3">
      Your browser does not support audio playback.
    </audio>
  </td>
</tr>

<tr class="shrink ralign">
  <td>half-second comb</td>
  <td>
    <audio controls>
      <source src="/assets/reverb/priorities-5.mp3" type="audio/mp3">
      Your browser does not support audio playback.
    </audio>
  </td>
</tr>

<tr class="shrink ralign">
  <td>10 millisecond comb</td>
  <td>
    <audio controls>
      <source src="/assets/reverb/priorities-01.mp3" type="audio/mp3">
      Your browser does not support audio playback.
    </audio>
  </td>
</tr>
</table>

<div class="remark">
The name "comb filter" comes from the effect that the comb filter has
in the [frequency domain](https://en.wikipedia.org/wiki/Frequency_domain):
it results in equally spaced peaks, like the tines of a comb.
</div>

Working with analog circuitry, a comb filter can be implemented with
a simple feedback loop, as shown below. Each time around
the loop, the signal is delayed and attenuated (scaled by some $$\alpha \in
[0,1]$$).

<img width="65%" src="/assets/reverb/comb.svg">

**Comb Filter Equation**.
Mathematically, a comb filter can be defined by the following equation.
We write $$S[i]$$ for the $$i$$<sup>th</sup> sample of the input,
and similarly $$C[i]$$ for a sample of the output. The constant $$D$$ is
the delay (measured in samples) between echoes, and
$$\alpha \in [0,1]$$ controls the intensity of each successive echo.
{: #comb-equation}

$$
C[i] = S[i] + \alpha C[i - D]
$$

## All-Pass Filters Are Fancy Combs
{: #all-pass-with-comb}

An [all-pass filter](https://en.wikipedia.org/wiki/All-pass_filter)
affects the
[phase](https://en.wikipedia.org/wiki/Phase_(waves)) of different frequencies,
shifting them around, causing the original sound to become "mis-aligned".
This is commonly used in electronic music to implement an effect
called a [phaser](https://en.wikipedia.org/wiki/Phaser_(effect)).
The name "all-pass" comes from the fact that all frequencies of the input
are allowed to "pass through", unmodified in strength.

A typical analog implementation of an all-pass circuit might look like this:

<img width="75%" src="/assets/reverb/allpass.svg">

Looking closely, notice that the all-pass circuit uses a feedback loop
which looks a lot like a comb filter. If
we rearrange some things, we can see that an all-pass filter is actually
just a comb filter with some extra machinery.

<img width="75%" src="/assets/reverb/allpass-with-comb.svg">

Mathematically, the following equation is another way of saying the same
thing. ($$S$$ is the input signal, $$C$$ is the result of combing the input, and
$$A$$ is the output of the all-pass.)

$$
A[i] = -\alpha S[i] + (1-\alpha^2) C[i-D]
$$

This is good news, because now we can focus on just implementing the comb
filter. Once we have it, we get an all-pass filter essentially for free.

## Parallel Comb Filter
{: #par-comb-section}

At a high level, the comb filter problem is to solve the
[comb filter equation](#comb-equation) $$C[i] = S[i] + \alpha C[i - D]$$,
where the inputs are $$S$$, $$\alpha$$, and $$D$$, and the output is $$C$$.

The parallel algorithm I came up with is based on two ideas.
  1. First, we can [split the problem into independent "columns"](#par-columns-comb).
  These columns can computed in parallel, however this
  does not expose enough parallelism on its own, especially for small values of
  $$D$$ (the delay parameter).
  2. Next, we can [parallelize each column](#geometric-prefix-sums). To do
  so, I identify a problem called ***geometric prefix-sums***. Each column is
  one instance of the geometric prefix-sums problem, and we can solve it
  by adapting a well-known algorithm for
  [parallel prefix-sums](https://en.wikipedia.org/wiki/Prefix_sum#Parallel_algorithms).

Combining the two ideas above, we get an algorithm for computing
the comb filter with $$O(N)$$ work and $$O(\log(N/D))$$ span, which is
work-efficient (asymptotically, it performs the same amount of work as the
fastest possible sequential algorithm) and highly parallel.

<div class="algorithm" name="(Parallel Comb Filter)">
[Split the input into columns](#par-columns-comb) and then in parallel compute
the [geometric prefix-sums](#geometric-prefix-sums) of the columns.
</div>
{: #parallel-comb-alg}

<div class="remark">
[Work and span](https://en.wikipedia.org/wiki/Analysis_of_parallel_algorithms)
are abstract cost measures of a parallel algorithm. The ***work*** is the
total number of operations performed, and the ***span*** is the number of
operations on the critical path (i.e. the longest chain of operations that
must occur sequentially one-by-one).

Given an algorithm with work $$W$$ and span $$S$$, a computer with $$P$$
processors can execute that algorithm in $$O(W/P + S)$$ time. Intuitively,
on each step the computer executes up to $$P$$ operations (one on each
processor), but there must be at least $$S$$ steps overall.
</div>

# Splitting Into Columns
{: #par-columns-comb}

The
[comb filter equation](#comb-equation) $$C[i] = S[i] + \alpha C[i - D]$$
can be broken up into $$D$$ independent computations.
Specifically, imagine laying out $$C$$ as a
matrix, where at row $$i$$ and column $$j$$ we put $$C[iD + j]$$.
In this layout, each column is a standalone computation, completely independent
of the values in the other columns. For example, as soon as we know the value
$$C[2]$$, we can immediately compute $$C[D+2]$$ and then $$C[2D+2]$$, etc.

<img width="60%" src="/assets/reverb/comb-columns.svg">

Since the columns are independent of one another, we can compute them in
parallel. But what do we do inside each column? We could proceed sequentially
from top to bottom... however, this does not provide
enough parallelism. One column
contains up to $$\lceil N / D \rceil$$ elements, leaving us
with $$O(N/D)$$ span, which for small values of $$D$$ is not very parallel
at all. Ideally, we'd like to be able to do a single column in logarithmic
span, say $$O(\log(N/D))$$.

# Parallelizing Each Column
{: #geometric-prefix-sums }

In this section, I show how each column is essentially a variant of the
[prefix-sums problem](https://en.wikipedia.org/wiki/Prefix_sum#Parallel_algorithms)
and describe how to adapt a well-known algorithm.

**Setting the Stage**.
The $$i$$<sup>th</sup> input of the $$j^\text{th}$$ column is $$S[iD+j]$$,
and similarly the outputs are $$C[iD+j]$$. Let's simplify the dicussion by defining
$$X[i] = S[iD+j]$$ and taking $$X$$ as our input sequence.
Then, abstractly, the problem we're trying to solve is to produce a sequence
$$Y$$ where $$Y[i] = C[iD+j]$$, i.e. the output column of combed samples.

With this setup, the [comb filter equation](#comb-equation) gives us the
following recurrence for $$Y$$.

$$
Y[i] = X[i] + \alpha Y[i-1]
$$

If we unroll this recurrence, we can see that each output element is a
prefix-sum of inputs scaled by powers of $$\alpha$$.

$$
Y[i] = \sum_{k=0}^i \alpha^{i-k} X[k]
$$

Let's call this problem the ***geometric prefix-sums problem***. We
can solve it with following algorithm, which I've adapted from a
[parallel prefix-sums algorithm](https://en.wikipedia.org/wiki/Prefix_sum#Parallel_algorithms).

<div class="algorithm" id="alg-geometric-prefix-sums" name="(Parallel Geometric Prefix-Sums)">

**Inputs**: $$\alpha \in [0,1]$$ and sequence $$X$$.

**Output**: sequence $$Y$$ where $$Y[i] = \sum_{k=0}^i \alpha^{i-k} X[k]$$.

The algorithm consists of three steps:
1. (Contraction Step) In parallel, combine adjacent input elements in "blocks"
of size 2. Specifically, for each even $$i$$, compute $$\alpha X[i] + X[i+1]$$.
These are called the ***block-sums***. Note that there are half as many
block-sums as input values, so we've reduced the problem in half.
2. (Recursive Step) Recursively compute the geometric prefix-sums of the block-sums.
In the recursive call, use $$\alpha^2$$ instead of $$\alpha$$.
The results of this step are the *odd indices of* $$Y$$.
3. (Expansion Step) Fill in the missing (even) indices by computing
$$Y[i] = X[i] + \alpha Y[i-1]$$ for each even $$i$$. Note that each $$Y[i-1]$$
is one of the outputs of the previous step.
</div>

Here's an example for an input of size 6.

<img width="80%" src="/assets/reverb/prefix-sums-contraction.svg">

Note that the results of the recursive call are *geometric prefix-sums of
block-sums*. For example, $$Y[3]$$ is the geometric prefix-sum
(using $$\alpha^2$$) of two block-sums:

<img width="55%" src="/assets/reverb/y3-breakdown.svg">

<!-- **Granularity Control**.
This algorithm works for any block-size,
giving us an opportunity for
[granularity control](https://en.wikipedia.org/wiki/Granularity_%28parallel_computing%29).
For a block-size $$B$$, we need to use a scaling factor of
$$\alpha^B$$ in the recursive step (instead of $$\alpha^2$$ as originally
described). Producing
the missing indices in the "expansion" step is also slightly more involved: the
first value within each output block is the same as before, but then we need
to continue scanning through the block to fill in the other nearby missing
indices. -->

**Work and Span**.
On an input of size $$M$$, the geometric prefix-sums algorithm
recursively uses a problem of size $$M/2$$ and otherwise does $$O(M)$$ work,
all of which is fully parallel. This yields the following work and span
recurrences, which solve to $$O(M)$$ work and $$O(\log M)$$ span.
* Work: $$W(M) = W(M/2) + O(M)$$
* Span: $$S(M) = S(M/2) + O(1)$$

Applying the geometric prefix-sums algorithm to a column of
size $$\lceil N/D \rceil$$, we have an algorithm for computing one column of
the comb filter in $$O(N/D)$$ work and $$O(\log(N/D))$$ span. In total,
for $$D$$ columns, that gives us a parallel comb algorithm with
$$O(N)$$ work and $$O(\log(N/D))$$ span. Nice!

# Making It Fast In Practice

Our parallel comb algorithm is fast in theory: it is asymptotically
***work-efficient*** (it performs the same amount of work as the fastest
possible sequential algorithm) and ***highly parallel*** (it has low
span---logarithmic, in this case).

**But is the algorithm fast in practice?**
If implemented exactly as described above, no! I tried this, and found that
a naive implementation of our parallel comb algorithm is as much as
*8 times slower* on one processor than a fast sequential implementation.

<div class="remark">
It's easy to make the mistake of focusing on
*scalability*, not raw speed. That is, I could have told you that my naive
code gets 7 times faster when I use 8 processors instead of 1, and that
would have seemed pretty good. But still, it's slower than the
sequential code, so
[what's the point](http://www.frankmcsherry.org/assets/COST.pdf)?

Simply put: my naive implementation is useless for less than 8 processors.
And even with more than 8 processors, it's still not very efficient to use 8
times as much energy just to get the same result back in slightly less time.
</div>

<!--(The fast sequential comb
algorithm is extremely simple: just output $$C[i]$$ according to the
[comb filter equation](#comb-equation) in increasing order of $$i$$
looking up previously output values $$C[i-D]$$ as needed.)-->
<!--on an input of size
22MB (about 4 minutes of audio with 16-bit samples at a sample rate of 44.1kHz),
the parallel code takes about 0.45 seconds, but the fast sequential code takes
only 0.06 seconds. That's a difference of 8x!-->

**To make the algorithm fast**, we need to reduce the amount of work it is
performing by nearly an order of magnitude. This might seem like a daunting
optimization task, but there are some really easy fixes we can make that will
get us most of the way there.

<!--
high constant factors, poor
[granularity control](https://en.wikipedia.org/wiki/Granularity_(parallel_computing)),
and poor
[cache utilization](https://en.wikipedia.org/wiki/Cache_%28computing%29).

Let's start with the granularity control problem.

For large values of $$D$$, the matrix is really wide but not very tall. In
this case, we could control granularity by doing a lot of columns together
as one unit.

For small values of $$D$$, the matrix is really tall but skinny.

Notice that the
[geometric prefix-sums algorithm](#alg-geometric-prefix-sums) w
-->
