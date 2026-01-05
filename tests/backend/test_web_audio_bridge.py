import asyncio

import numpy as np

from meshchatx.src.backend.web_audio_bridge import WebAudioSink, WebAudioSource


class _DummySink:
    def __init__(self):
        self.frames = []

    def can_receive(self, from_source=None):
        return True

    def handle_frame(self, frame, source):
        self.frames.append(frame)


def test_web_audio_source_pushes_frames():
    sink = _DummySink()
    src = WebAudioSource(target_frame_ms=60, sink=sink)
    zeros = np.zeros(160, dtype=np.int16)
    src.push_pcm(zeros.tobytes())
    assert len(sink.frames) == 1


def test_web_audio_sink_encodes_and_sends_bytes():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    sent = []

    async def _send_bytes(data):
        sent.append(data)

    sink = WebAudioSink(loop, _send_bytes)
    sink.handle_frame(np.zeros((160, 1), dtype=np.float32), None)
    loop.run_until_complete(asyncio.sleep(0.01))
    loop.close()
    assert sent, "expected audio bytes to be queued for sending"
