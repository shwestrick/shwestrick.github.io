---
layout: post
title:  "A Comb Filter is All You Need: Fast Parallel Reverb"
mathjax: true
---

In my quest to develop a wide range of interesting benchmarks for
[`mpl`](https://github.com/mpllang/mpl) (including for example the
*seam-carver* I described in my
[previous post]({% post_url 2020-07-29-seam-carve %})), I found myself
deep in the rabbit hole of designing a fast parallel algorithm for
artificial reverberation. I've now finished it, and the results are
quite satisfying.

TODO sound clips: original and with reverb, multiple reverb settings.
{: style="color:red"}

Reverb is essentially just a bunch of echoes all mashed together. To
generate these echoes, I used ***comb*** and ***all-pass*** filters, following
a design by
[Manfred Schroeder](https://en.wikipedia.org/wiki/Manfred_R._Schroeder)
as described by
[Curtis Roads](https://en.wikipedia.org/wiki/Curtis_Roads) in
[The Computer Music Tutorial](https://mitpress.mit.edu/books/computer-music-tutorial).
Both comb and all-pass filters produce regular echoes, although their spectral
effects are quite different. By carefully configuring and combining these
filters, we get a convincing artificial reverb effect.

Both types of filters (comb and all-pass) have obvious sequential algorithms
that are fast and extremely easy to implement. Deriving good parallel
algorithms for these filters, however, is not as straightforward.

In this
post, I describe the algorithms I developed and show that they perform well
in practice.

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
is essentially an echo generator. It produces periodic echoes of
a sound, where each successive echo is dimished in intensity.
This combines two effects: *attenuation* and *delay*.
Attenuating a signal makes it less intense, and delaying a signal makes it
"start" later.

<table class="images">
<tr>
  <td><img src="/assets/reverb/attenuate.svg">Attenuation</td>
  <td><img src="/assets/reverb/delay.svg">Delay</td>
</tr>
</table>

Below, I've drawn an example of applying a comb filter. The input
appears first, colored in blue, and each distinct echo is a different color.
(The actual output signal would be the sum of all
these echoes altogether as one signal, but I kept them separate in the
picture to help see what's going on.) I've also highlighted one sample from each
echo to illustrate the
[impulse response](https://en.wikipedia.org/wiki/Impulse_response)
of the filter: each sample is repeated (infinitely) many times as a series of
equally-spaced, decaying impulses.

<img src="/assets/reverb/comb-signal.svg">

**Analog Circuit**. Implementing a feedback comb filter as an analog
circuit is extremely simple, as shown below. Using
a feedback loop, we cause the signal to repeat after a delay, and this
occurs recursively so that these repeats are themselves repeated,
continuing indefinitely.
An attenuation parameter $$\alpha \in [0,1]$$ reduces the intensity of
each repeat.

<img width="70%" src="/assets/reverb/comb.svg">

# Sequential Comb Algorithm

To get a sequential algorithm for a comb filter, we can imagine feeding
samples through the analog circuit shown above. One-by-one, we take a sample
from the input, add it to the value of the feedback loop, and then pass this
along to the output. The values in the feedback loop are just values that
were output previously.

Here is the
[`mpl`](https://github.com/mpllang/mpl)
code for this algorithm. We represent the input and output signals as
sequences of samples, where each sample is a number in the range
$$[-1,+1]$$. Sequences are basically just arrays; we write `alloc n` allocate a
fresh (uninitialized) sequence of length `n`, and get and set the $$i^\text{th}$$
value of a sequence $$S$$ with `get S i` and `set S i x`.

{% highlight sml %}
(* D: the number of samples to delay in the feedback loop
 * a: the attenuation constant, in range [0,1]
 * input: the sequence of input samples.
 *)
fun sequentialComb (D: int) (a: real) (input: real seq) =
  let
    val n = length S
    val output = alloc n
  in
    for (0, n) (fn i =>
      (* this is executed for each i from 0 to n-1 *)
      if i < D then
        set output i (get input i)
      else
        set output i (get input i + a * get output (i - D))
    );
    output
  end
{% endhighlight %}

# Parallel Comb Algorithm

For a sequence of samples $$S$$, attenuation $$\alpha$$, and delay duration
$$D$$ (measured in samples), the combed samples $$S'$$ are given
by the following equation.

$$
S'[i] = \sum_{j=0}^{\lfloor i / D \rfloor} \alpha^j S[i - jD]
$$

<!--
To see why this is correct, let's walk through a small example.
Imagine running a signal through the circuit shown above
with a delay duration of $$D = 1$$ sample.
We'll write $$S = \langle s_0, s_1, s_2, \ldots \rangle$$ for the samples of
this signal. If we pause the circuit at each sample point and measure the
wires, we would see the following (showing the first three
samples):

<img width="70%" src="/assets/reverb/comb-steps.svg">

Initially, the first sample $$s_0$$ flows on the input through
to the output. On the next sample point, $$s_1$$ flows on the input and is
combined with the delayed $$\alpha s_0$$ from the feedback loop, producing
$$s_1 + \alpha s_0$$ on the output. This is fed back through the loop and
attenuated by $$\alpha$$, so that on the final sample point, $$s_2$$ is
combined with $$\alpha s_1 + \alpha^2 s_0$$ to produce
$$s_2 + \alpha s_1 + \alpha^2 s_0$$ on the output.

Altogether, on input $$S$$ with a delay time of one sample, we see that the
resulting signal $$S'$$ is

$$
S' = \langle s_0,\ s_1 + \alpha s_0,\ s_2 + \alpha s_1 + \alpha^2 s_0,\ \ldots \rangle
$$

-->

<!-- <div class="algorithm">
**Bad Comb Algorithm**

Inputs:
  * array $$S$$ of $$N$$ samples
  * attenuation $$\alpha$$
  * delay $$D$$ (measured in samples)

Output: array $$S'$$ of $$N$$ samples

Algorithm:
1. Allocate output array $$S'$$
2. In parallel for each $$0 \leq n < N$$:
  * Set $$S'[n] \gets \sum_{i=0}^{\left\lfloor{n/D}\right\rfloor} \alpha^i S[n - iD]$$
</div> -->

## Allpass Filter

<img width="80%" src="/assets/reverb/allpass.svg">

# Implementation

You might have noticed that the feedback loop of the allpass filter is
essentially just a comb filter. This will make our lives much simpler,
as we can reuse the fancy parallel implementation we developed for the
comb filter to generate an allpass filter.

## Putting it all together

The algorithm described here is one of many reverberators designed by
[Manfred Schroeder](https://en.wikipedia.org/wiki/Manfred_R._Schroeder) during
his time at Bell Labs. Schroeder presented multiple designs, but we will only
be considering one of them here.

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
