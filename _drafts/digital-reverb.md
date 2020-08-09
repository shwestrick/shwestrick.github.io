---
layout: post
title:  "How Digital Reverb Works: Comb Filters Everywhere!"
mathjax: true
---

In my quest to develop a range of interesting benchmarks for
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


## All-pass Filter

<img width="80%" src="/assets/reverb/allpass.svg">

An all-pass filter is essentially just a comb filter with some extra
machinery.

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
