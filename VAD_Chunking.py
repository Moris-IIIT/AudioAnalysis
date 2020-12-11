import collections
import contextlib
import sys
import wave
import os,path
import glob
import webrtcvad


def read_wave(path):
    """Reads a .wav file.
    Takes the path, and returns (PCM audio data, sample rate).
    """
    #print('ReadWav:\n')
    with contextlib.closing(wave.open(path, 'rb')) as wf:
        num_channels = wf.getnchannels()
        assert num_channels == 1
        sample_width = wf.getsampwidth()
        assert sample_width == 2
        sample_rate = wf.getframerate()
        assert sample_rate in (8000, 16000, 32000, 48000)
        pcm_data = wf.readframes(wf.getnframes())
        return pcm_data, sample_rate


def write_wave(path, audio, sample_rate):
    """Writes a .wav file.
    Takes path, PCM audio data, and sample rate.
    """
    with contextlib.closing(wave.open(path, 'wb')) as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio)


class Frame(object):
    """Represents a "frame" of audio data."""
    def __init__(self, bytes, timestamp, duration):
        self.bytes = bytes
        self.timestamp = timestamp
        self.duration = duration


def frame_generator(frame_duration_ms, audio, sample_rate):
    """Generates audio frames from PCM audio data.
    Takes the desired frame duration in milliseconds, the PCM data, and
    the sample rate.
    Yields Frames of the requested duration.
    """
    print('FrameGenerator:\n')
    n = int(sample_rate * (frame_duration_ms / 1000.0) * 2)
    offset = 0
    timestamp = 0.0
    duration = (float(n) / sample_rate) / 2.0
    while offset + n < len(audio):
        yield Frame(audio[offset:offset + n], timestamp, duration)
        timestamp += duration
        offset += n


def vad_collector(sample_rate, frame_duration_ms,
                  padding_duration_ms, vad, frames,time):
    """Filters out non-voiced audio frames.
    Given a webrtcvad.Vad and a source of audio frames, yields only
    the voiced audio.
    Uses a padded, sliding window algorithm over the audio frames.
    When more than 90% of the frames in the window are voiced (as
    reported by the VAD), the collector triggers and begins yielding
    audio frames. Then the collector waits until 90% of the frames in
    the window are unvoiced to detrigger.
    The window is padded at the front and back to provide a small
    amount of silence or the beginnings/endings of speech around the
    voiced frames.
    Arguments:
    sample_rate - The audio sample rate, in Hz.
    frame_duration_ms - The frame duration in milliseconds.
    padding_duration_ms - The amount to pad the window, in milliseconds.
    vad - An instance of webrtcvad.Vad.
    frames - a source of audio frames (sequence or generator).
    Returns: A generator that yields PCM audio data.
    """
    num_padding_frames = int(padding_duration_ms / frame_duration_ms)
    # We use a deque for our sliding window/ring buffer.
    ring_buffer = collections.deque(maxlen=num_padding_frames)
    # We have two states: TRIGGERED and NOTTRIGGERED. We start in the
    # NOTTRIGGERED state.
    triggered = False
    voiced_frames = []
    for frame in frames:
        is_speech = vad.is_speech(frame.bytes, sample_rate)

        #sys.stdout.write('1' if is_speech else '0')
        if not triggered:
            ring_buffer.append((frame, is_speech))
            num_voiced = len([f for f, speech in ring_buffer if speech])
            # If we're NOTTRIGGERED and more than 90% of the frames in
            # the ring buffer are voiced frames, then enter the
            # TRIGGERED state.
            if num_voiced > 0.9 * ring_buffer.maxlen:
                triggered = True
                sys.stdout.write('%d\t' % (round(float(ring_buffer[0][0].timestamp,))))
                #print(round(float(ring_buffer[0][0].timestamp)),' - ')
                #time.append(ring_buffer[0][0].timestamp)
                #timestamps.append('a')
                # We want to yield all the audio we see from now until
                # we are NOTTRIGGERED, but we have to start with the
                # audio that's already in the ring buffer.
                for f, s in ring_buffer:
                    voiced_frames.append(f)
                ring_buffer.clear()
        else:
            # We're in the TRIGGERED state, so collect the audio data
            # and add it to the ring buffer.
            voiced_frames.append(frame)
            ring_buffer.append((frame, is_speech))
            num_unvoiced = len([f for f, speech in ring_buffer if not speech])
            # If more than 90% of the frames in the ring buffer are
            # unvoiced, then enter NOTTRIGGERED and yield whatever
            # audio we've collected.
            if num_unvoiced > 0.99 * ring_buffer.maxlen:
                sys.stdout.write('%d' % (round(float(frame.timestamp + frame.duration))))
                #print(round(float(frame.timestamp + frame.duration)))
                #time.append(frame.timestamp + frame.duration)
                triggered = False
                yield b''.join([f.bytes for f in voiced_frames])
                ring_buffer.clear()
                voiced_frames = []
    if triggered:
        #sys.stdout.write('-(%s)' % (frame.timestamp + frame.duration))
        #print('Triggered')
        None
    #print('\n')
    # If we have any leftover voiced audio when we run out of input,
    # yield it.
    if voiced_frames:
        yield b''.join([f.bytes for f in voiced_frames])
        
def substring_after(s, delim):
    return s.partition(delim)[2]
def substring_before(s,extenstion):
    return s.partition(extenstion)[0]

filenames = glob.glob('/home/luvitusmaximus/Documents/ASR/SampleAudioFiles/WAVFiles/'+'*.wav')
#print(filenames)
directory = '/home/luvitusmaximus/Documents/ASR/SampleAudioFiles/WAVFiles/CHUNKS/'
newNames = []
delimiter = '/home/luvitusmaximus/Documents/ASR/SampleAudioFiles/WAVFiles/'
for file in filenames:
    name = substring_after(file,delimiter)
    name = substring_before(name,'.wav')
    #print(name,'\n')
    newNames.append(name)
time =[]
#print(newNames)
j = 0
for file in filenames:
    audio, sample_rate = read_wave(file)
    vad = webrtcvad.Vad(3)
    frames = frame_generator(30, audio, sample_rate)
    frames = list(frames)
    #print('------- File is  : ',file,'-------------','\n')
    segments = vad_collector(sample_rate, 30, 300, vad, frames,time)
    #print(time)
    for i, segment in enumerate(segments):
        path = directory + newNames[j] + '_%004d.wav' % (i+1,)
        print('\tWriting\t%s' % (path,))
        write_wave(path, segment, sample_rate)
    print('\n')
    j = j + 1 
