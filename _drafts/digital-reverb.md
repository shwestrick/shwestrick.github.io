---
layout: post
title:  "Implementing Parallel Digital Reverberation"
mathjax: true
---

Everyone is familiar with reverberation, or *reverb* for short. It's the
difference between singing in a closet and singing in a bathroom.
When you yell into a canyon and (after a moment) hear your voice echoed
back at you, this is essentially a form of reverb. What you're hearing
is your voice *reflected* back at you by hard surfaces on the other side
of the canyon.

All rooms are just tiny
canyons, with a lot more surfaces, and at much closer distances. Each surface
provides a different echo, which might come straight back to your ears, or
might bounce around the room for a while before you hear it. To simulate
the feeling of a room, we just need to simulate all of its
surfaces, and how these surfaces interact with one another, to create echoes
and resonances of the original sound.

Typical rooms have a lot of surfaces at weird angles (tables, chairs, etc.)
and just a few big flat surfaces, such as its four walls and ceiling. Roughly
speaking, we can simulate the sound of the big flat surfaces with just a
few "early reflections" of the sound, largely unmodified. For all of the
weird surfaces, we can generate

For decades now, reverb has been a quintessential component of digital sound
processing software. Many ways to generate digital reverb...

## A Simple Artificial Reverberator

The algorithm described here is one of many reverberators designed by
[Manfred Schroeder](https://en.wikipedia.org/wiki/Manfred_R._Schroeder) during
his time at Bell Labs. Schroeder's reverberators consist of two basic
components: ***comb*** and ***allpass*** filters (described in more detail in
the next section). Generally speaking, the comb filters are used to generate
regular reflections of the sound at various frequencies, and the allpass
filters help compound these reflections to generate a vast collection of
***fused reflections*** of the source signal. These fused reflections can
be mixed with the original signal to simulate reverberation.

Schroeder presented multiple designs, but we will only be considering one of
them here.

As audio is inherently a time-varying signal, many algorithms that manipulate
audio can be succinctly expressed as though they were analog circuits. We
imagine the audio signal flowing over the wires, fed into various components
which modify the signal somehow and spit it out on the other side.

 of two kinds of components: comb and
allpass filters. The overall design is to use four comb filters in parallel,
followed by two allpass filters in series, as shown in the following
diagram.

<img width="80%" src="/assets/reverb/design.svg">


Many signal-processing algorithms can be succinctly expressed as circuits,
where we imagine data flowing over wires in real-time.



Traditionally, perhaps due to its natural origin in analog circuitry, many

