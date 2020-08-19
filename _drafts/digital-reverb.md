---
layout: post
title:  "Digital Reverb: Fast Comb Filters Are All You Need"
mathjax: true
---

Generating convincing reverb turns out to be surprisingly simple, but making
it fast is not quite as easy!

In this post, I describe what a
[comb filter](https://en.wikipedia.org/wiki/Comb_filter)
is and how, by combining a bunch of these filters together, we can create
a digital reverberator. I then dive into some of the dirty details
of making the comb filter super fast, including designing a
parallel algorithm and optimizing it for practical efficiency.
I originally developed this algorithm as a parallel benchmark for
[`mpl`](https://github.com/mpllang/mpl), the compiler I'm developing at
Carnegie Mellon University. You can see the [source code on GitHub](??).

## What is Reverb?

Reverb is the effect that a room (or any space) has on sound. When a sound
is produced, it radiates from its source, hitting nearby surfaces and bouncing
unpredictably until eventually it loses so much energy that you can no longer
hear it.

Each room behaves differently, depending on its size, its shape, and its
contents. Compare, say, a bedroom closet to a cathedral.
A closet is small and full of shirts and linens and other soft things. If you
were to clap your hands, these soft objects would gobble up the noise, returning
you almost immediately to silence. But in a cathedral, the space is wide open,
and the walls are hard and far apart. When you clap your hands in a cathedral,
the noise comes alive.

<table class="images">
<tr>
  <td>
    <p>Clap in a closet</p>
  </td>
  <td>
    <p>Clap in a cathedral</p>
  </td>
</tr>

<tr>
  <td>
    <img src="/assets/reverb/dry-clap.svg">
  </td>
  <td>
    <img src="/assets/reverb/wet-clap.svg">
  </td>
</tr>

<tr>
  <td>
    <audio controls>
      <source src="/assets/reverb/dry-clap.mp3" type="audio/mp3">
      Your browser does not support audio playback.
    </audio>
  </td>
  <td>
    <audio controls>
      <source src="/assets/reverb/wet-clap.mp3" type="audio/mp3">
      Your browser does not support audio playback.
    </audio>
  </td>
</tr>
</table>

<!-- <div class="remark">
A brief sound is sometimes called an ***impulse***, and the sound of an
impulse within a room is called an
***[impulse response](https://en.wikipedia.org/wiki/Impulse_response)***.
The impulse response of a room is a good summary of its reverb
characteristics, and can be used to generate a convincing reverb effect
through a technique called
[convolution reverb](https://en.wikipedia.org/wiki/Convolution_reverb).
</div> -->

## Schroeder's Reverberator

The algorithm described here is one of many reverberators designed by
[Manfred Schroeder](https://en.wikipedia.org/wiki/Manfred_R._Schroeder) during
his time at Bell Labs. Schroeder presented multiple designs, but we will only
be considering one of them here, as described by
[Curtis Roads](https://en.wikipedia.org/wiki/Curtis_Roads) in
[The Computer Music Tutorial](https://mitpress.mit.edu/books/computer-music-tutorial).

Schroeder's design consists of two primary components: a *global reverator* and
a *tapped delay*. The goal of the global reverberator is to simulate the
overall response of a room, where there are thousands of echoes all
mixed together into a lush soup so dense that no one echo is distinctly
discernable. In contrast, the tapped delay produces just a few clearly distinct
echoes which reflect the sound straight back to the listener, simulating
a hard, flat wall in the back of the room. These are called
"early reflections" because they arrive first, almost immediately after the
original sound occurs. The global reverberation kicks in a moment later, and
then gradually dies down.

**Global Reverberator**. The overall design of the global reverberator is to
use four comb filters in parallel, followed by two allpass filters in series,
as shown in the following diagram.

<img width="80%" src="/assets/reverb/design.svg">

<!--
## Sampling

Real-world audio signals are *analog*. We could model a signal mathematically
by a function $$\mathbb{R} \to \mathbb{R}$$, but this doesn't immediately
translate to a digital world. The next best approximation we can do is to
***sample*** the signal at a regular frequency, and store the "heights"
of these discrete samples.

<img width="80%" src="/assets/reverb/sampling.svg">

It may appear as though sampling a signal *loses
information*, but surprisingly, this is not necessarily the case. In the
first half of the 20<sup>th</sup> century, multiple mathematicians proved that
you can perfectly reconstruct an analog signal as long as the ***sample rate***
is high enough. This result is known is as the
[Nyquist-Shannon sampling theorem](https://en.wikipedia.org/wiki/Nyquist%E2%80%93Shannon_sampling_theorem).

In this post, we'll be dealing with signals represented as sequences $$S$$ of
samples. Each $$S[i]$$ is one sample of the original signal.
For simplicity we will assume that $$i \in \mathbb{Z}$$
can be any integer, either positive or negative, extending as far as we
need in either direction. (Note however that in practice, the sequence will be
represented by an array and will "start" at index 0.)

When we use the notation $$S = \langle x, y, z, \ldots \rangle$$,
the intended meaning is that $$S[i] = 0$$ for all $$i < 0$$, and otherwise
$$S[0] = x$$, $$S[1] = y$$, $$S[2] = z$$, etc.
-->

## Comb Filter

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

Working with analog circuitry, we can achieve both effects at
the same time with a simple feedback loop, as shown below. Each time around
the loop, the signal is delayed
and attenuated (scaled by some $$\alpha \in [0,1]$$).

<img width="70%" src="/assets/reverb/comb.svg">

**Comb Filter Equation**.
When working with a [sampled signal](https://en.wikipedia.org/wiki/Sampling_%28signal_processing%29),
a comb filter can be defined by the following equation.
We write $$S[i]$$ for the $$i^\text{th}$$ sample of the input,
and similarly $$C[i]$$ for a sample of the output. The constant $$D$$ is
the delay (measured in samples) between echoes, and
$$\alpha \in [0,1]$$ controls the intensity of each successive echo.
{: #comb-equation}

$$
C[i] =
\begin{cases}
  S[i], &i < D \\
  S[i] + \alpha C[i - D], &\text{otherwise} \end{cases}
$$

## All-pass Filter

<img width="80%" src="/assets/reverb/allpass.svg">

An all-pass filter is essentially just a comb filter with some extra
machinery.

## Sequential Comb Filter
{: #seq-comb}

Sequentially, we can implement a comb filter by producing values
$$C[i]$$ in increasing order of
$$i$$ using the [equation given above](#comb-equation). Along the way, we need
to remember previous output values so that we can quickly retrieve the
each $$C[i-D]$$.

<div class="algorithm" name="(Sequential Comb Filter)">
On input $$S$$ of length $$N$$, sequentially output values $$C[i]$$ according
to [comb filter equation](#comb-equation) for each $$i$$ from $$0$$
to $$N$$.
</div>

In total, this algorithm perform $$O(N)$$ operations on an
input of size $$N$$, which is optimal---asymptotically, we can't do any better.

<!--
<div class="algorithm">
Here is the
[`mpl`](https://github.com/mpllang/mpl)
code for the sequential comb algorithm.

We represent the input and output signals as
sequences of samples, where each sample is a number in the range
$$[-1,+1]$$. Sequences are basically just arrays; we write `alloc n` allocate a
fresh (uninitialized) sequence of length `n`, and get and set the $$i^\text{th}$$
value of a sequence $$S$$ with `get S i` and `set S i x`.

{% highlight sml %}
(* D: the number of samples to delay in the feedback loop
 * a: the attenuation constant, in range [0,1]
 * S: the sequence of input samples.
 *)
fun sequentialComb (D: int) (a: real) (S: real seq) =
  let
    val n = length S
    val C = alloc n
  in
    for (0, n) (fn i =>
      (* this is executed once for each i from 0 to n-1 *)
      if i < D then
        set C i (get S i)
      else
        set C i (get S i + a * get C (i - D))
    );

    C
  end
{% endhighlight %}
</div>
-->

## Parallel Comb Filter

The parallel algorithm described here is based on two ideas.
  1. First, I describe how to [split the problem into independent "columns"](#par-columns-comb).
  These columns can be computed in parallel, however this does not expose
  enough parallelism on its own, especially for small values of $$D$$
  (the delay parameter).
  1. Next, I describe how to solve a
  [single column in parallel](#geometric-prefix-sums). I call this problem
  the ***geometric prefix-sums*** problem, and describe how to solve it by
  adapting a well-known algorithm for
  [parallel prefix-sums](https://en.wikipedia.org/wiki/Prefix_sum#Parallel_algorithms).

Combining the two ideas above, we get an algorithm for computing
the comb filter with $$O(N)$$ work and $$O(\log(N/D))$$ span, which is
work-efficient (asymptotically, it performs the same amount of work as the
fastest [sequential algorithm](#seq-comb)) and highly parallel.

<div class="algorithm" name="(Parallel Comb Filter)">
On input $$S$$,
[split the input into columns](#par-columns-comb) and then in parallel compute
the [geometric prefix-sums](#geometric-prefix-sums) of the columns.
</div>

<div class="remark">
[Work and span](https://en.wikipedia.org/wiki/Analysis_of_parallel_algorithms)
are abstract cost measures of a parallel algorithm. The ***work*** is the
total number of operations performed, and the ***span*** is the number of
operations on the critical path (i.e. the longest chain of operations that
must occur sequentially one-by-one).

Given an algorithm with work $$W$$ and span $$S$$, using $$P$$ processors,
we can execute that algorithm in $$O(W/P + S)$$ time. Intuitively,
on each step we perform up to $$P$$ operations (one on each processor), which
makes fast progress on the overall work, but there must be at least $$S$$ steps
overall.
</div>

# Parallelizing Across Columns
{: #par-columns-comb}

Let's look more closely at the
equation $$C[i] = S[i] + \alpha C[i - D]$$. Lurking in plain sight, this
equation contains $$D$$ completely independent computations which can
be computed in parallel.

To see the dependencies within $$C$$ more clearly,
imagine laying out $$C$$ in a matrix,
where at row $$i$$ and column $$j$$ we put $$C[iD + j]$$.
In this layout, each column is a standalone computation, completely independent
of the values in the other columns. For example, as soon as we know the value of
$$C[2]$$, we can immediately compute $$C[D+2]$$ and then $$C[2D+2]$$, etc.

<img width="60%" src="/assets/reverb/comb-columns.svg">

Since the columns are independent of one another, we can compute them in
parallel. But what do we do inside each column? We could proceed sequentially
from top to bottom, similar to the [sequential algorithm](#seq-comb) but
jumping by $$D$$ indices on each step; however, this does not provide
enough parallelism. One column
contains up to $$\lceil N / D \rceil$$ elements, leaving us
with $$O(N/D)$$ span, which for small values of $$D$$ is not very parallel
at all.

Ideally, we'd like to be able to do a single column in logarithmic
span, say $$O(\log(N/D))$$. In turns out this is possible! In the next section,
I describe how.

# Parallelizing Within Columns
{: #geometric-prefix-sums }

At first, it might appear as though the computation within
a column is entirely sequential. However, it turns out that there is quite
a lot of parallelism available.
In this section, I show how each column is essentially
a variant of the
[prefix-sums problem](https://en.wikipedia.org/wiki/Prefix_sum#Parallel_algorithms)
and describe how to adapt a well-known algorithm.

**Setting the Stage**.
The input elements on the $$j^\text{th}$$ column are elements $$S[iD+j]$$,
and the outputs are $$C[iD+j]$$. Let's simplify the dicussion by defining
$$X[i] = S[iD+j]$$ and taking $$X$$ as our input sequence.
Then, abstractly, the problem we're trying to solve is to produce a sequence
$$Y$$ where $$Y[i] = C[iD+j]$$, i.e. the output column of combed samples.

With this setup, the [comb filter equation](#comb-equation) gives us the
following recurrence for $$Y$$.

$$
Y[i] = \begin{cases} X[0], &i = 0 \\ X[i] + \alpha Y[i-1], &i > 0 \end{cases}
$$

If we unroll this recurrence, we can see that each output element is a
prefix-sum of inputs scaled by powers of $$\alpha$$.

$$
Y[i] = \sum_{k=0}^i \alpha^{i-k} X[k]
$$

Let's call this problem the ***geometric prefix-sums problem***. We
can solve it with following algorithm, which is adapted from an algorithm
for
[parallel prefix sums](https://en.wikipedia.org/wiki/Prefix_sum#Parallel_algorithms).

<div class="algorithm" id="alg-geometric-prefix-sums" name="(Parallel Geometric Prefix-Sums)">
For inputs $$\alpha$$ and $$X$$ and output $$Y$$, we do three steps.
1. In parallel, combine input elements in "blocks" of size 2. Each block
of $$X[i]$$ and $$X[i+1]$$ is transformed into $$\alpha X[i] + X[i+1]$$. These are called the
***block-sums***. Note that there are half as many block-sums as input values,
so we've reduced the problem in half.
2. Recursively compute the geometric prefix-sums of the block-sums.
In the recursive call, we scale by $$\alpha^2$$ instead of $$\alpha$$.
The results of this step are the *odd indices of* $$Y$$.
3. "Expand" to fill in the missing (even) indices by computing
$$Y[i] = X[i] + \alpha Y[i-1]$$ for each even $$i$$.
(The value $$Y[i-1]$$ is one of the outputs of the previous step!)
</div>

Here's an example for an input of size 6.

<img width="80%" src="/assets/reverb/prefix-sums-contraction.svg">

Note that the results of the recursive call are *geometric prefix-sums of
block-sums*. For example, $$Y[3]$$ is the geometric prefix-sum
(using $$\alpha^2$$) of two block-sums:

<img width="55%" src="/assets/reverb/y3-breakdown.svg">

**Granularity Control**.
This algorithm works for any block-size,
giving us an opportunity for
[granularity control](https://en.wikipedia.org/wiki/Granularity_%28parallel_computing%29).
For a block-size $$B$$, we need to use a scaling factor of
$$\alpha^B$$ in the recursive step (instead of $$\alpha^2$$ as originally
described). Producing
the missing indices in the "expansion" step is also slightly more involved: the
first value within each output block is the same as before, but then we need
to continue scanning through the block to fill in the other nearby missing
indices.

**Work and Span**.
On an input of size $$M$$, the
[geometric prefix-sums algorithm](#alg-geometric-prefix-sums)
recursively uses a problem of size $$M/2$$ (or $$M/B$$ in general, for
a block-size of $$B$$) and otherwise does $$O(M)$$ work, all of which is
fully parallel. This yields the following work and span recurrences,
which solve to $$O(M)$$ work and $$O(\log M)$$ span.
* Work $$W(M) = W(M/2) + O(M)$$.
* Span $$S(M) = S(M/2) + O(1)$$.

Applying this to a column of
size $$\lceil N/D \rceil$$, we have an algorithm for computing one column of
the comb filter in $$O(N/D)$$ work and $$O(\log(N/D))$$ span. Nice!

<!--
Concretely, the problem we're trying to solve is to take a column of input
values $$\langle S[i], S[i+D], S[i+2D], \ldots \rangle$$
and produce a column of output values
$$\langle C[i], C[i+D], C[i+2D], \ldots \rangle$$.

<img width="40%" src="/assets/reverb/columns-in-out.svg">

Let's simplify by renaming things a little. Let $$X$$ be the input, with
$$X_0 = S[i]$$, $$X_1 = S[i+D]$$, $$X_2 = S[i+2D]$$, etc. Similarly, let $$Y$$
be the output. Abstractly, then, the problem is to compute:

$$Y_i = X_i + \alpha Y_{i-1}$$

**A Contraction Algorithm**. The idea behind contraction is the solve a
problem recursively, in terms of a smaller version of itself. Specifically,
our goal here is to find new inputs $$X'$$ and $$\alpha'$$, and a new
output $$Y'$$, such that the same equation holds again:

$$Y_j' = X_j' + \alpha' Y_{j-1}'$$

To get there, let's unroll the original equation a little:

$$
\begin{align*}
  Y_i
  &= X_i + \alpha Y_{i-1} \\
  &= X_i + \alpha \color{red}{\left(X_{i-1} + \alpha Y_{i-2}\right)}
  &&\text{(unroll definition of $Y_{i-1}$)} \\
  &= \left(X_i + \alpha X_{i-1}\right) + \alpha^2 Y_{i-2}
  &&\text{(rearrange)}
\end{align*}
$$

Now we're getting somewhere! Do you see it? We can rename the indices a little
to make it clear. Let's use a new index $$j$$ with $$2j+1 = i$$:

$$
\begin{align*}
  Y_i &= \left(X_i + \alpha X_{i-1}\right) + \alpha^2 Y_{i-2}
  \\
  Y_\color{red}{2j+1} &= \left(X_\color{red}{2j+1} + \alpha X_{\color{red}{2j}}\right) + \alpha^2 Y_{\color{red}{2j-1}}
  &&(\text{let}\ 2j+1 = i)
  \\
  \color{red}{Y_j'} &= \left(X_{2j} + \alpha X_{2j-1}\right) + \alpha^2 \color{red}{Y_{j-1}'}
  &&(\text{let}\ Y_j' = Y_{2j+1})
  \\
  Y_j' &= \color{red}{X_j'} + \alpha^2 Y_{j-1}'
  &&(\text{let}\ X_j' = X_{2j+1} + \alpha X_{2j})
  \\
  Y_j' &= X_j' + \color{red}{\alpha'} Y_{j-1}'
  &&(\text{let}\ \alpha' = \alpha^2)
\end{align*}
$$

This sets up the smaller instance of the problem. It is "smaller" in the sense
that $$X'$$ and $$Y'$$ have half as many elements as $$X$$ and $$Y$$.

The output of the smaller instance gives us a bunch of values $$Y_j'$$, which
are each equal to $$Y_{2j+1}$$. That is, **the smaller instance provides the
odd indices of the output**. That leaves us with needing to compute the
even indices, which is easy: for every unknown value at an even index,
there's a known value at the previous odd index which can be used to fill
in the missing value.

<div class="algorithm">
We define a function
$$\textsf{ParallelColumn}(\alpha, X, N)$$ for input $$X$$ of length $$N$$.
The index arithmetic is outrageously tedious, but fairly straightforward.

$$
\begin{array}{l}
&\textsf{ParallelColumn}(\alpha, X, N) =
\\
&~~~~\text{let}~~X' = \big\langle X[2j+1] + \alpha X[2j] : 0 \leq j < \lfloor N / 2 \rfloor \big\rangle
  \\
&~~~~\text{let}~~Y' = \textsf{ParallelColumn}(\alpha^2, X', \lfloor N / 2 \rfloor)
  \\
&~~~~\text{let}~~Y(i) =
    \begin{cases}
      X[0], &i = 0 \\
      Y'[(i-1) / 2], &\text{$i$ odd} \\
      X[i] + \alpha Y'[(i/2)-1], &\text{$i$ even}
    \end{cases}
  \\
&~~~~\text{return}~~\big\langle Y(i) : 0 \leq i < N \big\rangle
\end{array}
$$

In [`mpl`](https://github.com/mpllang/mpl), the code is as follows.
{% highlight sml %}
fun parallelColumn (alpha: real) (X: real seq) =
  if length X <= 1 then
    X
  else
    let
      val N = length X
      val X' = tabulate (N div 2) (fn j =>
        get X (2*j+1) + alpha * get X (2*j)
      )
      val Y' = parallelColumn (alpha * alpha) X'
      val Y = tabulate N (fn i =>
        if i = 0 then
          get X 0
        else if isOdd i then
          get Y' (i div 2)
        else
          get X i + alpha * get Y' (i div 2 - 1)
      )
    in
      Y
    end
{% endhighlight %}
</div>
-->
