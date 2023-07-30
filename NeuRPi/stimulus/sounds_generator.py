import numpy as np
import sounddevice as sd
from scipy.io import wavfile

def generate_audio(freq, duration, ramp_up, sample_rate, phase):
    # Calculate the number of samples based on the duration and sample rate
    num_samples = int(duration * sample_rate)

    # Create an array of time values for the duration
    time = np.linspace(0, duration, num_samples, endpoint=False)

    # Generate the audio waveform with the specified frequency and phase
    # using a sinusoidal signal
    audio_signal = np.sin(2 * np.pi * freq * time + phase)

    # Apply the ramp-up by multiplying the signal with a ramp-up envelope
    ramp_up_samples = int(ramp_up * sample_rate)
    ramp_up_envelope = np.linspace(0, 1, ramp_up_samples)
    audio_signal[:ramp_up_samples] *= ramp_up_envelope

    return audio_signal

def play_audio(audio_signal, sample_rate):
    # Play the audio using the sounddevice library
    sd.play(audio_signal, samplerate=sample_rate)
    sd.wait()  # Wait until the audio finishes playing

if __name__ == "__main__":
    freq = 5000  # 5 KHz
    duration = 0.1  # 100 ms
    ramp_up = 0.01  # 10 ms
    sample_rate = 192000  # 192 KHz
    phase = 2 * np.pi * np.random.rand()  # Random phase between 0 and 2*pi radians

    audio_signal = generate_audio(freq, duration, ramp_up, sample_rate, phase)


    # Save the audio signal to a WAV file
    output_file = "generated_audio.wav"
    wavfile.write(output_file, sample_rate, audio_signal)

    # Play the audio using the sounddevice library
    sd.play(audio_signal, samplerate=sample_rate)
    sd.wait()  # Wait until the audio finishes playing
