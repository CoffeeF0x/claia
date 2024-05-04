import sounddevice as sd
import soundfile as sf

def record_sound(duration=5, filename='output.wav', fs=44100):
    """Record sound from the microphone and save it to a file."""
    print("Recording...")
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=2)
    sd.wait()  # Wait until recording is finished
    sf.write(filename, recording, fs)
    print("Recording complete. Saved as", filename)

def play_sound(filename):
    """Play a sound file."""
    data, fs = sf.read(filename)
    print(f"Playing {filename}...")
    sd.play(data, fs)
    sd.wait()  # Wait until playback is finished
    print("Playback complete.")

def main():
    # Record and play back the mic recording
    recorded_file = 'output.wav'
    record_sound(duration=5, filename=recorded_file)
    play_sound(recorded_file)

    # # Path to the test WAV file in the 'samples' directory
    # test_file = 'samples/test.wav'

    # # Play the test WAV file
    # play_sound(test_file)

if __name__ == "__main__":
    main()
