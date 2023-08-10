import numpy as np
import scipy.io.wavfile


def generate_sound(frequency, duration, ramping_time, sampling_rate):
    """
    Generate sinewave sounds at a given frequency for specified duration with sampling rate and optional ramping_time, and save sound as .wav file
    """
    # Generate sound
    t = np.linspace(0, duration, int(sampling_rate * duration))
    sound = np.sin(2 * np.pi * frequency * t)
    # Add ramping
    if ramping_time:
        ramp = np.linspace(0, 1, int(ramping_time * sampling_rate))
        sound[: len(ramp)] = sound[: len(ramp)] * ramp
        sound[-len(ramp) :] = sound[-len(ramp) :] * ramp[::-1]

    # Scale sound to 16-bit range (optional, if needed for compatibility with Pygame)
    sound = (sound * 32767).astype(np.int16)

    # Save sound
    scipy.io.wavfile.write("sound.wav", sampling_rate, sound)
    return sound


if __name__ == "__main__":
    # Solve error aplay: test_wavefile:1131:  can't play WAVE-files with sample 64 bits wide
    # https://stackoverflow.com/questions/45596189/why-cant-i-play-a-wav-file-with-aplay

    generate_sound(frequency=5000, duration=0.1, ramping_time=0.01, sampling_rate=192000)
