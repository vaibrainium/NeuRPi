import numpy as np
import scipy.io.wavfile


def generate_sound(filename, frequency, duration, ramping_time, sampling_rate, volume):
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

    # Scale sound by the volume
    sound = sound * volume

    # Scale sound to 16-bit range (optional, if needed for compatibility with Pygame)
    sound = (sound * 32767).astype(np.int16)

    # Save sound
    scipy.io.wavfile.write(filename, sampling_rate, sound)
    return sound


if __name__ == "__main__":
    # Solve error aplay: test_wavefile:1131:  can't play WAVE-files with sample 64 bits wide
    # https://stackoverflow.com/questions/45596189/why-cant-i-play-a-wav-file-with-aplay

    # fixation onset
    # generate_sound(filename="fixation_tone_ramp.wav", frequency=5000, duration=0.1, ramping_time=0.01, sampling_rate=192000, volume=.2)
    # # stimulus onset
    # generate_sound(frequency=5000, duration=0.1, ramping_time=0.01, sampling_rate=192000)
    # # correct response
    # generate_sound(filename="correct_tone.wav", frequency=1000, duration=0.3, ramping_time=0.01, sampling_rate=192000, volume=1)

    # generate_sound(filename="left_direction_tone.wav", frequency=8000, duration=60, ramping_time=0.0, sampling_rate=192000, volume=.2)
    # generate_sound(filename="right_direction_tone.wav", frequency=16000, duration=60, ramping_time=0.0, sampling_rate=192000, volume=1)

    generate_sound(filename="8KHz_2sec.wav", frequency=8000, duration=2, ramping_time=0.05, sampling_rate=192000, volume=0.2)
    generate_sound(filename="16KHz_2sec.wav", frequency=16000, duration=2, ramping_time=0.05, sampling_rate=192000, volume=1)
